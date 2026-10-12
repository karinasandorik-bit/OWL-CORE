"""Stripe provider contract checks; no remote Stripe traffic or charges."""
import pytest
from stripe_contract import Decision,stripe_v1_recovery

BASE=dict(sandbox=True,post=True,age_seconds=60,frozen_payload_matches=True,
          same_account=True,receipt_verified=False,reconciliation_complete=False,
          stripe_should_retry=None,ambiguous=True)

def check(**changes):
    return stripe_v1_recovery(**{**BASE,**changes})

def test_timeout_same_key_within_window_is_admissible_not_executed():
    assert check()==Decision.RETRY_SAME_KEY

@pytest.mark.parametrize("age",[23*3600,24*3600,25*3600,None,-1])
def test_expiration_or_missing_timestamp_blocks_retry(age):
    assert check(age_seconds=age)==Decision.RECONCILE

@pytest.mark.parametrize("kw",[
    {"sandbox":False},{"post":False},{"same_account":False},
    {"ambiguous":False},{"stripe_should_retry":False}])
def test_missing_scope_or_provider_no_retry(kw):
    assert check(**kw)==Decision.HOLD

def test_payload_mismatch_blocks_retry():
    assert check(frozen_payload_matches=False)==Decision.RECONCILE

def test_verified_receipt_is_not_another_post():
    assert check(receipt_verified=True)==Decision.ACCEPT_RECEIPT

def test_reconciled_object_is_not_another_post():
    assert check(reconciliation_complete=True)==Decision.RECONCILE
