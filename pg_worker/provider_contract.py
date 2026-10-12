"""Fail-closed provider contract: transport timeout is never proof of no commit.
Pure policy, safe for isolated CI and production read-only assessment.
"""
from dataclasses import dataclass
from enum import Enum
from reconcile import reconcile, Verdict

class Action(str, Enum):
    CONFIRM="confirm"
    HOLD="hold_unknown"
    REVIEW="manual_review"
    RETRY="retry_same_key"

@dataclass(frozen=True)
class Contract:
    provider_name: str
    atomic_idempotency: bool
    durable_key_lookup: bool
    lookup_strongly_consistent: bool
    payload_bound_to_key: bool
    receipt_independently_verifiable: bool
    key_retention_exceeds_recovery: bool

    @property
    def safe_retry(self):
        return all((self.atomic_idempotency,self.durable_key_lookup,
                    self.lookup_strongly_consistent,self.payload_bound_to_key,
                    self.receipt_independently_verifiable,
                    self.key_retention_exceeds_recovery))

def decide(contract, key, lookup, verify_receipt, transport_error=None):
    # Never equate timeout/connection reset/5xx with NOT_FOUND.
    verdict, receipt=reconcile(key,lookup,verify_receipt)
    if verdict==Verdict.CONFIRMED:
        return Action.CONFIRM,receipt
    if verdict==Verdict.UNKNOWN:
        return Action.HOLD,None
    # NOT_FOUND is insufficient absent *all* contract guarantees.
    if not contract.safe_retry:
        return Action.REVIEW,None
    # Only retry the exact same immutable key and payload, behind an
    # independently permissioned actuator; this module never sends POST.
    return Action.RETRY,None
