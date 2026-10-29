"""Protocol model tests use only invented bytes, mock authority and volatile memory."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from equipment_data_manager.publication_model import SandboxSnapshot, MockReviewerAuthority, MemoryPublicationModel
from equipment_data_manager.processing.models import ProcessingError


def snapshot(selection='synthetic-selection-1', amount=b'invented financial summary'):
    return SandboxSnapshot(selection, (('repairs.csv',b'invented repairs'),
        ('repair_financial_summary.csv',amount),('service_orders.csv',b'invented services'),
        ('tma_work_orders.csv',b'invented work orders')))


@pytest.fixture
def model():
    authority = MockReviewerAuthority(('synthetic-reviewer',))
    return authority, MemoryPublicationModel(authority)


def publish(authority, model, value):
    grant = authority.issue('synthetic-reviewer',value)
    model.stage(value,grant,current_selection=lambda:value.selection_fingerprint)
    model.select(value,grant,expected_generation=model.generation,current_selection=lambda:value.selection_fingerprint)
    return grant


@pytest.mark.parametrize('grant', [None,'typed-admin-name','checked-approved'])
def test_missing_approval_rejected_before_staging(model, grant):
    _, publisher = model
    with pytest.raises(ProcessingError,match='missing_or_stale_approval'):
        publisher.stage(snapshot(),grant,current_selection=lambda:'synthetic-selection-1')
    assert publisher.staging == {} and publisher.current is None


def test_unauthorized_reviewer_cannot_issue_grant(model):
    authority, publisher = model
    with pytest.raises(ProcessingError,match='unauthorized_reviewer'):
        authority.issue('not-in-synthetic-allowlist',snapshot())
    assert publisher.current is None


@pytest.mark.parametrize('change',['candidate','source_hash','summary_hash'])
def test_corrected_revision_source_or_output_hash_requires_fresh_grant(model, change):
    authority, publisher = model
    original = snapshot()
    grant = authority.issue('synthetic-reviewer',original)
    corrected = snapshot(selection='changed-'+change)
    with pytest.raises(ProcessingError,match='missing_or_stale_approval'):
        publisher.stage(corrected,grant,current_selection=lambda:corrected.selection_fingerprint)
    with pytest.raises(ProcessingError,match='candidate_changed'):
        publisher.stage(original,grant,current_selection=lambda:corrected.selection_fingerprint)
    assert publisher.current is None


def test_missing_report_or_duplicate_names_rejected(model):
    authority, _ = model
    for files in [snapshot().files[:-1],snapshot().files+(snapshot().files[0],)]:
        with pytest.raises(ProcessingError,match='incomplete_snapshot'):
            authority.issue('synthetic-reviewer',SandboxSnapshot('synthetic',files))


def test_interrupted_upload_retains_previous_and_partial_snapshot_can_resume(model):
    authority, publisher = model
    previous = snapshot()
    publish(authority,publisher,previous)
    new = snapshot('synthetic-correction',b'invented corrected summary')
    grant = authority.issue('synthetic-reviewer',new)
    calls=[]
    def interrupt(name,raw):
        calls.append(name)
        if len(calls)==2:
            raise TimeoutError('simulated interruption')
        return raw
    with pytest.raises(TimeoutError):
        publisher.stage(new,grant,current_selection=lambda:new.selection_fingerprint,transfer=interrupt)
    assert publisher.current == previous.identity
    assert len(publisher.staging[new.identity])==1
    with pytest.raises(ProcessingError,match='partial_snapshot'):
        publisher.select(new,grant,expected_generation=1,current_selection=lambda:new.selection_fingerprint)
    publisher.stage(new,grant,current_selection=lambda:new.selection_fingerprint)
    assert publisher.select(new,grant,expected_generation=1,current_selection=lambda:new.selection_fingerprint)=='selected'
    assert publisher.published[previous.identity] == previous


def test_transfer_integrity_failure_cannot_select_partial_set(model):
    authority,publisher=model
    value=snapshot(); grant=authority.issue('synthetic-reviewer',value)
    with pytest.raises(ProcessingError,match='transfer_integrity_failed'):
        publisher.stage(value,grant,current_selection=lambda:value.selection_fingerprint,transfer=lambda name,raw:b'corrupt')
    assert publisher.current is None and publisher.published=={}


def test_duplicate_publication_is_idempotent_and_does_not_duplicate_history(model):
    authority,publisher=model
    value=snapshot(); grant=publish(authority,publisher,value)
    assert publisher.select(value,grant,expected_generation=0,current_selection=lambda:value.selection_fingerprint)=='already_selected'
    assert len(publisher.events)==1 and len(publisher.published)==1


def test_concurrent_employees_cannot_overwrite_pointer(model):
    authority,publisher=model
    values=[snapshot('synthetic-first'),snapshot('synthetic-second')]
    grants=[authority.issue('synthetic-reviewer',v) for v in values]
    for value,grant in zip(values,grants):
        publisher.stage(value,grant,current_selection=lambda:value.selection_fingerprint)
    def attempt(pair):
        value,grant=pair
        try:
            return publisher.select(value,grant,expected_generation=0,current_selection=lambda:value.selection_fingerprint)
        except ProcessingError as exc:
            return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,zip(values,grants)))
    assert sorted(results)==['model_selection_conflict','selected']
    assert publisher.generation==1 and len(publisher.events)==1


def test_correction_during_transfer_blocks_final_selection(model):
    authority,publisher=model
    value=snapshot();grant=authority.issue('synthetic-reviewer',value)
    publisher.stage(value,grant,current_selection=lambda:value.selection_fingerprint)
    with pytest.raises(ProcessingError,match='candidate_changed'):
        publisher.select(value,grant,expected_generation=0,current_selection=lambda:'corrected')
    assert publisher.current is None


def test_rollback_needs_distinct_current_generation_approval_and_preserves_history(model):
    authority,publisher=model
    first,second=snapshot(),snapshot('synthetic-second')
    original_grant=publish(authority,publisher,first)
    publish(authority,publisher,second)
    with pytest.raises(ProcessingError,match='missing_or_stale_approval'):
        publisher.rollback(first.identity,original_grant,expected_generation=2)
    rollback=authority.issue('synthetic-reviewer',first,operation='rollback',generation=2)
    assert publisher.rollback(first.identity,rollback,expected_generation=2)=='selected_previous_snapshot'
    assert publisher.current==first.identity and len(publisher.published)==2 and publisher.generation==3
    with pytest.raises(ProcessingError,match='selection_conflict'):
        publisher.rollback(first.identity,rollback,expected_generation=2)
    with pytest.raises(ProcessingError,match='rollback_target_unavailable'):
        publisher.rollback('nonexistent',rollback,expected_generation=3)
