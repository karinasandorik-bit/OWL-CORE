"""Adversarial decision table for ambiguous commits; no real external writes."""
import pytest
from provider_contract import Contract,Action,decide

GOOD=Contract("isolated",True,True,True,True,True,True)
BAD=Contract("unverified",False,False,False,False,False,False)
RECEIPT={"idempotency_key":"k1","provider_tx":"tx-k1"}

@pytest.mark.parametrize("error",["timeout","connection_reset","http_500","worker_sigkill",None])
def test_confirmed_commit_even_if_response_lost(error):
    action,receipt=decide(GOOD,"k1",lambda k:RECEIPT,
                          lambda r:r["provider_tx"]=="tx-k1",error)
    assert action==Action.CONFIRM and receipt==RECEIPT

@pytest.mark.parametrize("error",["timeout","connection_reset","http_500","worker_sigkill"])
def test_ambiguous_lookup_unavailable_never_retry(error):
    action,_=decide(GOOD,"k1",lambda k:(_ for _ in ()).throw(TimeoutError()),
                    lambda r:True,error)
    assert action==Action.HOLD

@pytest.mark.parametrize("field",[
    "atomic_idempotency","durable_key_lookup","lookup_strongly_consistent",
    "payload_bound_to_key","receipt_independently_verifiable",
    "key_retention_exceeds_recovery"])
def test_missing_one_guarantee_forbids_retry(field):
    d={k:getattr(GOOD,k) for k in GOOD.__dataclass_fields__}
    d[field]=False
    assert decide(Contract(**d),"k1",lambda k:None,lambda r:True,"timeout")[0]==Action.REVIEW

def test_not_found_with_fully_verified_contract_allows_only_same_key_retry():
    assert decide(GOOD,"k1",lambda k:None,lambda r:True,"timeout")[0]==Action.RETRY

def test_bad_receipt_is_unknown_not_retry():
    assert decide(GOOD,"k1",lambda k:{"idempotency_key":"other"},
                  lambda r:True,"timeout")[0]==Action.HOLD
    assert decide(GOOD,"k1",lambda k:RECEIPT,
                  lambda r:False,"timeout")[0]==Action.HOLD

def test_unverified_provider_requires_manual_review():
    assert decide(BAD,"k1",lambda k:None,lambda r:True,"timeout")[0]==Action.REVIEW
