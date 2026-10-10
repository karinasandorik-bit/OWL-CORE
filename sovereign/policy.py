"""Fail-closed authorization and evidence gate for OWL SOVEREIGN."""
from dataclasses import dataclass
from enum import Enum
class State(str,Enum):
    EXECUTED="EXECUTED"
    DERIVED="DERIVED"
    HYPOTHESIS="HYPOTHESIS"
    BLOCKED="BLOCKED"
    VERIFIED="VERIFIED"
SAFE=frozenset({"public_research","read_only_github_search","hypothesis","preregistration","ablation","branch_write","test","propose_pr","lead_qualification","draft_deliverable","read_only_market_data","shadow_signals","independent_api_check","outcome_verification"})
SENSITIVE=frozenset({"transfer_funds","sign_arbitrary","live_trade","paid_spend","auto_merge","client_submission","production_deploy","payment_reconciliation"})
@dataclass(frozen=True)
class Grant:
    action:str
    scope:str
    expires_at:int
    approved:bool=False
def authorize(action:str,scope:str,now:int,grant:Grant|None=None)->bool:
    if action in SAFE:return True
    if action not in SENSITIVE:return False
    return bool(grant and grant.approved and grant.action==action and grant.scope==scope and grant.expires_at>now)
def verified_income(amount:float,external_settlement_id:str|None,source_verified:bool)->bool:
    return amount>0 and bool(external_settlement_id) and source_verified
