"""Future Entra authentication/authorization boundary; no SDK or token operations.

These display contracts cannot grant approval. The default provider fails closed.
"""
from dataclasses import dataclass
from typing import Protocol
from equipment_data_manager.processing.models import ProcessingError


@dataclass(frozen=True)
class IdentityReadiness:
    authentication: str
    reviewer_authorization: str
    explanation: str


@dataclass(frozen=True, repr=False)
class ReviewerVerification:
    """Future service evidence, NOT trusted merely because this object exists.

    Future approval must independently validate issuer/signature/audience/tenant,
    subject, policy, expiry, revocation and exact resource/selection/action binding.
    No current application method accepts this as approval or publication authority.
    """
    tenant_id: str
    subject_id: str
    selection_fingerprint: str
    report_month: str
    action: str
    policy_version: str
    authority_evidence_reference: str
    expires_at: str


class ReviewerIdentityProvider(Protocol):
    def readiness(self) -> IdentityReadiness: ...
    def sign_in(self) -> None: ...
    def verify_reviewer(self, *, selection_fingerprint: str, report_month: str,
                        action: str) -> ReviewerVerification: ...


class UnavailableReviewerIdentity:
    def readiness(self):
        return IdentityReadiness('not_configured', 'not_verified',
            'Microsoft Entra sign-in is unavailable. Reviewer roles and permission verification are not configured.')

    def sign_in(self):
        raise ProcessingError('review_identity_unavailable')

    def verify_reviewer(self, **kwargs):
        raise ProcessingError('review_authority_unavailable')
