"""Fail-closed controller: observation -> decision -> bounded action -> independent proof."""
import hashlib
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class Observation:
    operation_id: str
    source: str
    observed_digest: str
    status: int

@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    operation_id: str

def decide(observation: Observation) -> Decision:
    if not observation.operation_id or not observation.observed_digest:
        return Decision('BLOCK', 'missing_evidence', observation.operation_id)
    if observation.status == 404:
        return Decision('CREATE_CANARY', 'absent_remote_canary', observation.operation_id)
    if observation.status == 200:
        return Decision('RECONCILE', 'existing_remote_canary', observation.operation_id)
    return Decision('BLOCK', f'untrusted_status_{observation.status}', observation.operation_id)

def verify(observation: Observation, decision: Decision, result: dict) -> dict:
    if decision.action == 'BLOCK':
        raise ValueError('blocked_decision')
    if result.get('operation_id') != observation.operation_id:
        raise ValueError('operation_mismatch')
    if result.get('remote_digest') != observation.observed_digest:
        raise ValueError('digest_mismatch')
    if result.get('remote_commit_count') != 1:
        raise ValueError('side_effect_count_mismatch')
    if result.get('outbox_state') != 'verified' or result.get('recovery_workers') != 2 or result.get('kill_exit') != -9:
        raise ValueError('recovery_proof_missing')
    payload = {'operation_id': observation.operation_id, 'observation': observation.source,
               'decision': decision.action, 'outcome': 'VERIFIED', 'remote_sha': result.get('remote_sha')}
    if not payload['remote_sha']:
        raise ValueError('remote_sha_missing')
    payload['evidence_digest'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload
