"""No Entra/Graph access; presentation contracts do not confer business authority."""
from decimal import Decimal
import pytest
from test_review_requests import reviewing
from equipment_data_manager.auth.reviewer_identity import UnavailableReviewerIdentity, ReviewerVerification
from equipment_data_manager.ui.review_presenter import review_sections
from equipment_data_manager.review import ReviewService
from equipment_data_manager.processing.repair_financial import powerbi_coordinator
from equipment_data_manager.processing.models import ProcessingError


def test_default_identity_provider_cannot_sign_in_or_verify_a_claimed_role():
    provider=UnavailableReviewerIdentity()
    assert provider.readiness().authentication=='not_configured'
    assert provider.readiness().reviewer_authorization=='not_verified'
    with pytest.raises(ProcessingError,match='review_identity_unavailable'):
        provider.sign_in()
    with pytest.raises(ProcessingError,match='review_authority_unavailable'):
        provider.verify_reviewer(subject_id='typed-name',role='Administrator',authorized=True)


def test_a_constructed_identity_contract_cannot_authorize_approval(tmp_path):
    evidence=ReviewerVerification('synthetic-tenant','synthetic-subject','invented-selection','2026-01',
        'approve','synthetic-policy','unverified-reference','2099-01-01T00:00:00Z')
    service=ReviewService(powerbi_coordinator(tmp_path/'candidates'))
    with pytest.raises(ProcessingError,match='review_approval_unavailable'):
        service.approve(evidence)
    assert not service.root.exists()


def test_employee_sections_use_labels_and_preserve_full_revision_evidence(reviewing):
    _,_,service=reviewing
    captured=service.capture('2026-01')
    result=review_sections(dict(captured=captured,history=[]))
    assert 'Repair Reports: 3 retained / 3 source rows' in result['counts']
    assert 'Reported monthly total: $30.00' in result['financial']
    assert 'Missing values' in result['issues']
    for selected in captured['evidence']['selected']:
        assert selected['revision'] in result['revisions']
        assert selected['source_sha256'] in result['revisions'] and selected['output_sha256'] in result['revisions']
    assert '{' not in result['counts']+result['financial']+result['issues']+result['history']


@pytest.mark.parametrize('status',['ReviewRequestedLocallyNotSent','StaleSelectionChanged','StaleOrUnavailable','Approved','Published','ApprovalPending'])
def test_local_or_forged_status_never_proves_later_business_states(reviewing,status):
    _,_,service=reviewing
    captured=service.capture('2026-01')
    record=dict(request_id='synthetic-id',requested_at='2026-01-01T00:00:00+00:00',status=status,evidence_note='Synthetic reference')
    result=review_sections(dict(captured=captured,history=[record]))
    assert result['stages'][0][1]==('Recorded here — not sent' if status=='ReviewRequestedLocallyNotSent' else 'Not recorded for current evidence')
    assert result['stages'][1:]==(('Approval Pending','Not submitted to an approval service'),
        ('Approved','No authoritative approval evidence'),('Published','Unavailable — publishing disabled'))


def test_null_financial_values_are_not_formatted_as_zero_and_missing_month_is_clear(reviewing):
    _,_,service=reviewing
    captured=service.capture('2026-01')
    summary=captured['evidence']['reports']['repairs']['financial_summary']
    summary['ReportedTotalCost']=None; summary['ReportedPartsCost']='0.00'
    result=review_sections(dict(captured=captured,history=[]))
    assert 'Reported monthly total: Not supplied / unresolved' in result['financial']
    assert 'Reported monthly parts: $0.00' in result['financial']
    empty=review_sections(dict(captured=service.capture('2026-03'),history=[]))
    assert empty['counts'].count('MISSING')==3
