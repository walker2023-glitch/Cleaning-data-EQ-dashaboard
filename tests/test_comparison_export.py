"""Synthetic comparison contracts, evidence, failure isolation and compatibility."""
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from threading import Event

import pytest

from equipment_data_manager import comparison_export as module
from equipment_data_manager.comparison_export import (
    FIELDS, LINEAGE_FIELDS, NAMES, generate_comparison, validate_comparison,
)
from equipment_data_manager.processing.models import ProcessingError
from test_historical_dataset import selected, build
from equipment_data_manager.historical_dataset import preview_dataset


def tree(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()}


def rows(path):
    return list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8'), newline='')))


@pytest.fixture
def source(tmp_path):
    workspace = selected(tmp_path, (1, 2))
    plan = preview_dataset(workspace, '2026-01', '2026-02')
    return workspace, build(workspace, plan, tmp_path / 'canonical')


def create(source, destination, **kwargs):
    workspace, snapshot = source
    return generate_comparison(workspace, snapshot, destination, confirmed=True, export_schema=module.EXPORT_SCHEMA, **kwargs)


def test_repeatable_projections_lineage_and_retained_evidence_without_source_writes(source, tmp_path):
    workspace, snapshot = source
    canonical_before, candidates_before, raw_before = tree(snapshot), tree(workspace.candidate_folder), tree(workspace.raw_folder)
    first, second = [create(source, tmp_path / f'comparison-{i}') for i in (1, 2)]
    assert tree(first) == tree(second)
    manifest = validate_comparison(first)
    assert manifest['export_schema'] == 'comparison-preview-v1'
    assert manifest['purpose'] == 'DevelopmentComparison' and not manifest['production_ready']
    assert manifest['approval_status'] == 'NotApproved'
    assert manifest['source_manifest_sha256'] == sha256((snapshot / 'snapshot_manifest.json').read_bytes()).hexdigest()
    assert tree(first / 'audit/canonical') == canonical_before == tree(snapshot)
    assert tree(workspace.candidate_folder) == candidates_before and tree(workspace.raw_folder) == raw_before
    evidence = rows(first / 'audit/lineage.csv')
    assert list(evidence[0]) == list(LINEAGE_FIELDS)
    for kind, name in NAMES.items():
        original, projected = rows(snapshot / name), rows(first / name)
        assert len(projected) == len(original)
        assert list(projected[0]) == list(FIELDS[kind])
        assert projected == [{key: row[key] for key in FIELDS[kind]} for row in original]
        links = [r for r in evidence if r['Dataset'] == name]
        assert len(links) == len(original)
        for ordinal, (link, row) in enumerate(zip(links, original), 1):
            assert link['ExportRecordNumber'] == link['CanonicalRecordNumber'] == str(ordinal)
            assert all(link[key] == row.get(key, '') for key in LINEAGE_FIELDS[3:])
    tma = rows(first / NAMES['tma_work_orders'])
    assert len({r['WorkOrderId'] for r in tma}) < len(tma)  # Repeated business IDs survive.
    assert any(r['EquipmentId'].startswith('0') for r in rows(first / NAMES['service_orders']))
    assert not workspace.approved_folder.exists()


def test_nullable_zero_and_unknown_money_are_not_reinterpreted(tmp_path):
    from test_historical_processing import prepare, preview, plan_for, execute
    from test_repair_financial import raw_report
    workspace, _, _ = prepare(tmp_path)
    repair = workspace.raw_folder / '2026/2026-01 (January)/CompuClean Repair Report.csv'
    repair.write_bytes(raw_report(costs=['$0.00', '', 'bad']))
    inventory, batch = preview(workspace, '2026-01', '2026-01')
    execute(workspace, inventory, plan_for(workspace, inventory, batch))
    plan = preview_dataset(workspace, '2026-01', '2026-01')
    canonical = build(workspace, plan, tmp_path / 'canonical')
    output = create((workspace, canonical), tmp_path / 'comparison')
    repairs = rows(output / NAMES['repairs'])
    assert [r['ReportedTotalCost'] for r in repairs] == ['0.00', '', '']
    summary = rows(output / NAMES['repair_financial_summary'])[0]
    assert summary['KnownRepairTotalCost'] == '0.00'
    assert summary['UnavailableRepairCostCount'] == '2' and summary['RepairTotalDifference'] == ''
    assert all(r['EstimatedPrice'] == '' for r in rows(output / NAMES['service_orders']))
    assert validate_comparison(output)


@pytest.mark.parametrize('fault', ['csv_hash', 'report_hash', 'columns', 'type', 'control_type', 'version', 'missing'])
def test_invalid_canonical_source_never_creates_output(source, tmp_path, fault):
    _, snapshot = source
    kind = 'repair_financial_summary' if fault == 'control_type' else 'repairs'
    path = snapshot / NAMES[kind]
    manifest_path = snapshot / 'snapshot_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if fault == 'csv_hash':
        path.write_bytes(path.read_bytes() + b'bad')
    elif fault == 'report_hash':
        (snapshot / 'compatibility_report.md').write_text('Changed')
    elif fault == 'missing':
        path.unlink()
    elif fault == 'version':
        manifest['snapshot_schema'] = 'unknown'
        manifest_path.write_text(json.dumps(manifest))
    else:
        content = rows(path)
        fields = list(content[0])
        if fault == 'columns':
            fields[fields.index('EquipmentId')] = 'WrongId'
            for row in content: row['WrongId'] = row.pop('EquipmentId')
        elif fault == 'control_type':
            content[0]['EstimatedLaborCostSum'] = 'not-money'
        else:
            content[0]['ReportedTotalCost'] = 'not-money'
        raw = module._encode(content, fields)
        path.write_bytes(raw)
        entry = next(e for e in manifest['datasets'] if e['report_type'] == kind)
        entry['sha256'] = sha256(raw).hexdigest()
        entry['columns'] = fields
        manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ProcessingError): create(source, tmp_path / 'comparison')
    assert not (tmp_path / 'comparison').exists()


def test_source_changed_between_validation_and_capture_fails(source, tmp_path, monkeypatch):
    original = module.validate_dataset
    def change(path):
        result = original(path)
        (path / NAMES['repairs']).write_bytes((path / NAMES['repairs']).read_bytes() + b'bad')
        return result
    monkeypatch.setattr(module, 'validate_dataset', change)
    with pytest.raises(ProcessingError, match='source_changed'): create(source, tmp_path / 'comparison')
    assert not (tmp_path / 'comparison').exists()


@pytest.mark.parametrize('fault', ['projection', 'lineage', 'canonical', 'manifest', 'extra', 'rehashed_projection'])
def test_completed_comparison_rejects_changed_outputs_or_evidence(source, tmp_path, fault):
    output = create(source, tmp_path / 'comparison')
    if fault in ('projection', 'rehashed_projection'):
        path = output / NAMES['repairs']
        path.write_bytes(path.read_bytes().replace(b'2026-01', b'2026-03', 1))
        if fault == 'rehashed_projection':
            path = output / module.MANIFEST_NAME
            manifest = json.loads(path.read_text())
            manifest['datasets'][0]['sha256'] = sha256((output / NAMES['repairs']).read_bytes()).hexdigest()
            path.write_text(json.dumps(manifest))
    elif fault == 'lineage':
        path = output / 'audit/lineage.csv'; path.write_bytes(path.read_bytes() + b'bad')
    elif fault == 'canonical':
        path = output / 'audit/canonical' / NAMES['repairs']; path.write_bytes(path.read_bytes() + b'bad')
    elif fault == 'manifest':
        path = output / module.MANIFEST_NAME
        manifest = json.loads(path.read_text()); manifest['approval_status'] = 'Approved'
        path.write_text(json.dumps(manifest))
    else:
        (output / 'extra.csv').write_text('unexpected')
    with pytest.raises(ProcessingError): validate_comparison(output)


def test_collision_preserves_existing_export_and_requires_explicit_intent(source, tmp_path):
    destination = tmp_path / 'comparison'
    output = create(source, destination)
    before = tree(output)
    with pytest.raises(ProcessingError, match='destination_exists'): create(source, destination)
    assert tree(output) == before
    with pytest.raises(ProcessingError, match='confirmation_required'):
        generate_comparison(source[0], source[1], tmp_path / 'unconfirmed')
    assert not (tmp_path / 'unconfirmed').exists()


@pytest.mark.parametrize('location', ['raw', 'candidates', 'approved', 'source', 'ancestor', 'OneDrive'])
def test_protected_roots_and_sync_locations_rejected(source, tmp_path, location):
    workspace, canonical = source
    destination = {'raw': workspace.raw_folder / 'out', 'candidates': workspace.candidate_folder / 'out',
        'approved': workspace.approved_folder / 'out', 'source': canonical / 'out',
        'ancestor': tmp_path, 'OneDrive': tmp_path / 'OneDrive' / 'out'}[location]
    with pytest.raises(ProcessingError): create(source, destination)


@pytest.mark.parametrize('where', ['source', 'destination'])
@pytest.mark.parametrize('predicate', ['is_symlink', 'is_junction'])
def test_linked_paths_rejected(source, tmp_path, monkeypatch, where, predicate):
    link = tmp_path / 'link'
    original = getattr(Path, predicate)
    monkeypatch.setattr(Path, predicate, lambda p: p == link or original(p))
    with pytest.raises(ProcessingError, match='link_rejected'):
        if where == 'source': create((source[0], link), tmp_path / 'comparison')
        else: create(source, link / 'comparison')


def test_windows_preflight_includes_deep_canonical_audit_files(source, tmp_path):
    with pytest.raises(ProcessingError, match='path_too_long'):
        module._destination(source[0], source[1], tmp_path / ('a' * 180), windows=True)
    assert module._destination(source[0], source[1], tmp_path / 'short', windows=True)


@pytest.mark.parametrize('fault', ['write', 'rename', 'cancel', 'interrupt', 'verification'])
def test_failures_cleanup_only_owned_container_and_keep_completed_versions(source, tmp_path, monkeypatch, fault):
    previous = create(source, tmp_path / 'previous')
    before, source_before = tree(previous), tree(source[1])
    write, rename = module._write, Path.rename
    stopped = Event()
    destination = tmp_path / 'new'
    def writing(path, raw):
        write(path, raw)
        if path.name == NAMES['service_orders']:
            if fault == 'write': raise OSError('Synthetic storage failure')
            if fault == 'interrupt': raise KeyboardInterrupt()
            if fault == 'cancel': stopped.set()
    def renaming(path, other):
        if path == destination / '.s' and fault == 'rename': raise OSError('Synthetic rename failure')
        return rename(path, other)
    def invalid(_): raise ProcessingError('comparison_contract_rejected')
    monkeypatch.setattr(module, '_write', writing)
    monkeypatch.setattr(Path, 'rename', renaming)
    if fault == 'verification': monkeypatch.setattr(module, 'validate_comparison', invalid)
    with pytest.raises((ProcessingError, OSError, KeyboardInterrupt)):
        create(source, destination, cancelled=stopped.is_set)
    assert not destination.exists()
    assert tree(previous) == before and tree(source[1]) == source_before


def test_cancel_before_start_creates_nothing(source, tmp_path):
    with pytest.raises(ProcessingError, match='cancelled'):
        create(source, tmp_path / 'comparison', cancelled=lambda: True)
    assert not (tmp_path / 'comparison').exists()


def test_m_helper_has_exact_typed_contract_and_no_recursive_ingestion():
    text = Path('powerquery/fnReadComparisonPreview.pq').read_text()
    for kind in FIELDS:
        body = re.search(r'\b' + kind + r' = \{([^\n]+)\}', text).group(1)
        assert re.findall(r'\{"([^"]+)", "([^"]+)"', body) == [(c.name, c.data_type) for c in module.schema(kind)]
    assert 'comparison-preview-v1' in text and 'DevelopmentComparison' in text
    assert 'Folder.Files' not in text and 'File.Contents' in text
    assert 'type nullable number' in text and 'type text' in text


def test_cli_verifies_and_safely_reports_invalid_input(source, tmp_path, capsys):
    output = create(source, tmp_path / 'comparison')
    module.main(['--verify', str(output)])
    assert 'Comparison integrity passed' in capsys.readouterr().out
    with pytest.raises(SystemExit) as failure: module.main(['--verify', str(tmp_path / 'missing')])
    assert failure.value.code == 1 and 'Comparison stopped' in capsys.readouterr().err
