"""Invented reports only; no authoritative approval service is configured."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from hashlib import sha256
import json
import sqlite3

import pytest
from test_powerbi_readiness import build
from test_repair_financial import raw_report
from equipment_data_manager.review import ReviewService
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest


@pytest.fixture
def reviewing(tmp_path):
    workspace, _, _, _, _ = build(tmp_path)
    from equipment_data_manager.processing.repair_financial import powerbi_coordinator
    engine = powerbi_coordinator(workspace.candidate_folder)
    return workspace, engine, ReviewService(engine, raw_folder=workspace.raw_folder)


def test_capture_counts_costs_missing_warnings_and_exact_identity_without_writes(reviewing):
    workspace, engine, service = reviewing
    captured = service.capture('2026-01')
    assert not service.root.exists() and not workspace.approved_folder.exists()
    evidence = captured['evidence']
    assert not evidence['missing_reports'] and evidence['publication'] == 'disabled'
    assert [r['retained_rows'] for r in evidence['reports'].values()] == [3,3,3]
    assert Decimal(evidence['reports']['repairs']['financial_summary']['ReportedTotalCost']) == Decimal('30')
    assert evidence['reports']['service_orders']['missing_values']
    for selected in evidence['selected']:
        assert selected['source_check'] == 'local_original_bytes_match'
        assert len(selected['source_sha256']) == len(selected['output_sha256']) == 64
        assert len(selected['revision']) == 32
    assert len(next(s for s in evidence['selected'] if s['report_type']=='repairs')['summary_sha256']) == 64


def test_local_request_is_durable_deduplicated_and_never_business_approval(reviewing):
    _, engine, service = reviewing
    captured = service.capture('2026-01')
    record = service.request('2026-01', captured['fingerprint'], 'Synthetic reconciliation evidence reviewed locally')
    assert record['status'] == 'ReviewRequestedLocallyNotSent'
    assert record['approval'] is None and record['reviewer_identity'] is None
    assert record['requested_at'].endswith('+00:00')
    assert service.request('2026-01', captured['fingerprint'], record['evidence_note']) == record
    reopened = ReviewService(engine, raw_folder=service.raw_folder)
    assert reopened.history() == [record]
    assert reopened.status(record) == 'ReviewRequestedLocallyNotSent'


@pytest.mark.parametrize('action', ['approve','publish'])
def test_final_actions_fail_closed_even_with_claimed_identity_and_checkbox(reviewing, action):
    _, _, service = reviewing
    with pytest.raises(ProcessingError, match='unavailable|disabled'):
        getattr(service, action)(reviewer='claimed-admin', authorized=True, approved=True)
    assert not service.root.exists()


def test_unauthorized_caller_cannot_convert_request_status(reviewing):
    _, _, service = reviewing
    record = service.request('2026-01', service.capture('2026-01')['fingerprint'], 'Synthetic evidence')
    record['approval'] = True
    record['reviewer_identity'] = 'unverified person'
    with pytest.raises(ProcessingError, match='unauthorized_reviewer'):
        service.status(record)


def test_corrected_source_stales_old_request_and_blocks_old_preview(reviewing):
    workspace, engine, service = reviewing
    captured = service.capture('2026-01')
    record = service.request('2026-01', captured['fingerprint'], 'Synthetic evidence')
    path = workspace.raw_folder/'2026-01/repairs/raw.csv'
    path.write_bytes(path.read_bytes().replace(b'$10.00', b'$11.00'))
    assert service.status(record) == 'StaleOrUnavailable'
    with pytest.raises(ProcessingError, match='review_source_changed'):
        service.request('2026-01', captured['fingerprint'], 'Synthetic evidence')
    request = ProcessingRequest('repairs','2026-01',input_path=path)
    pending = engine.process(request)
    from dataclasses import replace
    result = engine.process(replace(request,replacement_token=pending.replacement_token))
    assert result.status == 'success'
    assert service.status(record) == 'StaleSelectionChanged'
    with pytest.raises(ProcessingError, match='review_selection_changed'):
        service.request('2026-01', captured['fingerprint'], 'Synthetic evidence')
    assert service.history() == [record]


def test_missing_reports_visible_request_blocked_without_side_effects(reviewing):
    _, _, service = reviewing
    captured = service.capture('2026-03')
    assert len(captured['evidence']['missing_reports']) == 3
    with pytest.raises(ProcessingError, match='review_missing_reports'):
        service.request('2026-03', captured['fingerprint'], 'Missing monthly exports')
    assert not service.root.exists()


def test_tampered_output_or_financial_summary_blocks_review(reviewing):
    _, engine, service = reviewing
    entry = next(e for e in engine.store.history() if e.period=='2026-01' and e.report_type.value=='repairs')
    entry.artifact.output_path.write_bytes(b'changed')
    with pytest.raises(ProcessingError, match='hash_mismatch'):
        service.capture('2026-01')


def test_missing_original_is_an_explicit_gap_not_verified_sync(reviewing):
    workspace, _, service = reviewing
    (workspace.raw_folder/'2026-01/service_orders/raw.csv').unlink()
    captured = service.capture('2026-01')
    selected = next(s for s in captured['evidence']['selected'] if s['report_type']=='service_orders')
    assert selected['source_check'].startswith('original_unavailable:')
    assert captured['evidence']['sync_verified'] is False


def test_parallel_requests_create_one_append_only_record(reviewing):
    _, _, service = reviewing
    captured = service.capture('2026-01')
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda _: service.request('2026-01', captured['fingerprint'], 'Same synthetic evidence'), range(2)))
    assert records[0] == records[1] and len(service.history()) == 1
    path = service.root/'requests.sqlite3'
    with sqlite3.connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError, match='append only'):
            db.execute('DELETE FROM requests')
        db.execute('DROP TRIGGER no_update')
        db.execute("UPDATE requests SET body='{}'")
    with pytest.raises(ProcessingError, match='review_audit_integrity_failed'):
        service.history()


@pytest.mark.parametrize('note', ['', ' ', 'x'*4001, None])
def test_evidence_note_required_and_bounded(reviewing, note):
    _, _, service = reviewing
    with pytest.raises(ProcessingError, match='review_evidence_required'):
        service.request('2026-01', service.capture('2026-01')['fingerprint'], note)
    assert not service.root.exists()


def test_nullable_financial_evidence_is_retained_without_becoming_zero_or_approved(tmp_path):
    workspace, _, _, _, _ = build(tmp_path, raw_factory=lambda month:raw_report(month,costs=['$10.00','','0.00']))
    from equipment_data_manager.processing.repair_financial import powerbi_coordinator
    service=ReviewService(powerbi_coordinator(workspace.candidate_folder),raw_folder=workspace.raw_folder)
    captured=service.capture('2026-01')
    report=captured['evidence']['reports']['repairs']
    assert report['missing_values']['ReportedTotalCost']==1
    assert report['financial_summary']['RepairTotalDifference'] is None
    assert report['financial_reconciliation']=='incomplete_repair_costs_or_excluded_records'
    record=service.request('2026-01',captured['fingerprint'],'Request advice about missing source cost')
    assert record['approval'] is None


def test_failed_request_write_retains_selected_candidates_and_old_audit(reviewing,monkeypatch):
    workspace,engine,service=reviewing
    captured=service.capture('2026-01')
    old=service.request('2026-01',captured['fingerprint'],'Original synthetic evidence')
    before=engine.store.history()
    real_connect=sqlite3.connect
    def denied(database,*args,**kwargs):
        if str(database)==str(service.root/'requests.sqlite3'):
            raise sqlite3.OperationalError('simulated local lock or write failure')
        return real_connect(database,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(sqlite3,'connect',denied)
        with pytest.raises(sqlite3.OperationalError):
            service.request('2026-01',captured['fingerprint'],'New synthetic note')
    assert service.history()==[old] and engine.store.history()==before
    assert not workspace.approved_folder.exists()


def test_previous_powerbi_repair_schema_gets_explicit_review_upgrade_message(tmp_path):
    workspace, _, _, _, _=build(tmp_path,v1=True)
    from equipment_data_manager.processing.repair_financial import powerbi_coordinator
    service=ReviewService(powerbi_coordinator(workspace.candidate_folder),raw_folder=workspace.raw_folder)
    with pytest.raises(ProcessingError,match='review_requires_repair_v2'):
        service.capture('2026-01')
    assert not service.root.exists()
