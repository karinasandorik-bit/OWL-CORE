"""Read-only provider reconciliation. NEVER retry ambiguous HTTP commits blindly.
The provider must expose a durable lookup by idempotency key and return signed
or independently verifiable receipt data. No HTTP transport is bundled here.
"""
from enum import Enum
class Verdict(str,Enum):
    CONFIRMED="confirmed"
    NOT_FOUND="not_found"
    UNKNOWN="unknown"

def reconcile(idempotency_key, provider_lookup, verify_receipt):
    if not idempotency_key: raise ValueError("missing idempotency key")
    try:
        receipt=provider_lookup(idempotency_key)
    except Exception:
        return Verdict.UNKNOWN,None
    if receipt is None:
        # NOT_FOUND is not permission to retry unless provider documents
        # strongly consistent lookup plus atomic idempotency-key enforcement.
        return Verdict.NOT_FOUND,None
    if receipt.get("idempotency_key") != idempotency_key:
        return Verdict.UNKNOWN,None
    if not verify_receipt(receipt):
        return Verdict.UNKNOWN,None
    return Verdict.CONFIRMED,receipt
