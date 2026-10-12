"""Stripe API v1 recovery policy — no network calls, no payment authority.

Official docs: https://docs.stripe.com/error-low-level#idempotency
An API v1 idempotency key can be pruned after 24h. There is no generic
guaranteed lookup by key; reconciliation requires object IDs, request logs,
webhook evidence, or support. Test/sandbox mode is mandatory for integration tests.
"""
from enum import Enum

class Decision(str, Enum):
    HOLD = "hold_unknown"
    RECONCILE = "reconcile_external"
    RETRY_SAME_KEY = "retry_same_key"
    ACCEPT_RECEIPT = "accept_verified_receipt"

def stripe_v1_recovery(*, sandbox, post, age_seconds, frozen_payload_matches,
                       same_account, receipt_verified, reconciliation_complete,
                       stripe_should_retry=None, ambiguous=True):
    if not sandbox or not post or not same_account:
        return Decision.HOLD
    if receipt_verified:
        return Decision.ACCEPT_RECEIPT
    if reconciliation_complete:
        return Decision.RECONCILE
    # HTTP timeout/5xx does not prove whether side effect occurred.
    if not ambiguous:
        return Decision.HOLD
    if stripe_should_retry is False:
        return Decision.HOLD
    # Buffer inside documented >=24h retention window for clock skew.
    # This is an offline admission decision, not authorization for POST.
    if (age_seconds is None or age_seconds < 0 or age_seconds >= 23*3600
            or not frozen_payload_matches):
        return Decision.RECONCILE
    return Decision.RETRY_SAME_KEY
