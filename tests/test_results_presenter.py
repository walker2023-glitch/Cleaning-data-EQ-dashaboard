"""Employee outcome wording cannot manufacture successful persistence."""
from types import SimpleNamespace
from pathlib import Path
import pytest
from equipment_data_manager.processing.models import ProcessingResult, ProcessingStatus as S, OutputRevision
from equipment_data_manager.ui.results_presenter import outcome, counts, summary, run_message, next_step
from equipment_data_manager.ui.messages import result_label, diagnostic_lines


def result(status=S.SUCCESS,code='processed',saved=True,warnings=()):
    artifact=OutputRevision('revision',Path('candidate.csv'),'source','output','cleaner',3,2) if saved else None
    return ProcessingResult(status,code,artifact=artifact,warnings=warnings)


def entries(*results):return tuple(SimpleNamespace(result=r) for r in results)


@pytest.mark.parametrize('status,code,saved,group,label',[
    (S.SUCCESS,'processed',True,'saved','Saved successfully'),
    (S.SUCCESS,'previewed',False,'review','Needs review'),
    (S.SKIPPED,'already_processed',True,'unchanged','Already processed / unchanged'),
    (S.NEEDS_REVIEW,'replacement_confirmation_required',False,'review','Needs review'),
    (S.FAILURE,'input_changed_since_preview',False,'failed','Failed'),
    (S.FAILURE,'cancelled',False,'stopped','Stopped / not processed'),
])
def test_outcomes_require_real_engine_evidence(status,code,saved,group,label):
    r=result(status,code,saved)
    assert outcome(r)==group
    assert result_label(r)==label
    assert next_step(r).startswith('Next:')


def test_partial_failure_summary_stopped_and_warnings_remain_distinct():
    items=entries(result(warnings=('repair_cost_mapping_unverified',)),result(S.SKIPPED),
        result(S.NEEDS_REVIEW,saved=False),result(S.FAILURE,'processing_failed',False),
        result(S.FAILURE,'cancelled',False))
    assert counts(items)==dict(saved=1,unchanged=1,review=1,failed=1,stopped=1,warnings=1)
    text=run_message(items)
    assert text.startswith('Run finished with failed reports.')
    assert '1 failed' in text and '1 stopped' in text
    assert 'With warnings: 1' in summary(items)
    assert 'no production approval' in text


@pytest.mark.parametrize('results,caption',[
    (entries(),'No reports were processed.'),
    (entries(result()),'Run finished.'),
    (entries(result(S.SKIPPED)),'Run finished.'),
    (entries(result(S.FAILURE,'cancelled',False)),'Run stopped;'),
    (entries(result(S.NEEDS_REVIEW,saved=False)),'Run finished with reports needing review.'),
    (entries(result(saved=False)),'Run finished with reports needing review.'),
])
def test_completion_is_not_an_all_reports_success_claim(results,caption):
    assert run_message(results).startswith(caption)


def test_preview_does_not_claim_to_save_a_report():
    assert result_label(result(saved=False),preview=True)=='New report'


def test_diagnostic_business_summary_preserves_counts_but_moves_identity_to_details(tmp_path):
    from equipment_data_manager.ui.workflow import DesktopWorkflow,selected_files
    from threading import Event
    w=DesktopWorkflow(tmp_path/'candidate')
    preview=w.preview(selected_files(['tests/fixtures/synthetic/repairs_input.csv']),
        'repairs','2026-09',lambda *_:None,Event())[0]
    diagnostic=preview.result.diagnostics
    assert diagnostic is not None
    business='\n'.join(diagnostic_lines(diagnostic,technical=False))
    technical='\n'.join(diagnostic_lines(diagnostic))
    assert 'Source records:' in business and 'Reporting month:' in business
    assert 'SHA-256' not in business and 'Cleaner:' not in business
    assert 'Source SHA-256:' in technical and 'Local date trace' in technical
