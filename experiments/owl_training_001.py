"""OWL LAB synthetic policy-gate exercises. No external side effects."""
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class Task:
    track: str
    name: str
    action: str
    authorized: bool = True
    contrast: float = 7.0
    editable: bool = True
    receipt: bool = True
    repeated: bool = False
    expected: bool = True

TASKS = [
    Task('architecture','scoped_grant','deploy',authorized=True),
    Task('architecture','revoked_grant','deploy',authorized=False,expected=False),
    Task('architecture','read_only','inspect',authorized=True),
    Task('design','accessible_editorial','publish',contrast=7.0,editable=True),
    Task('design','low_contrast','publish',contrast=2.0,expected=False),
    Task('design','raster_only','publish',editable=False,expected=False),
    Task('operations','confirmed_delivery','settle',receipt=True),
    Task('operations','missing_receipt','settle',receipt=False,expected=False),
    Task('operations','duplicate_delivery','settle',repeated=True,expected=False),
]

def baseline(t):
    return True

def guarded(t):
    if not t.authorized: return False
    if t.track == 'design' and (t.contrast < 4.5 or not t.editable): return False
    if t.track == 'operations' and (not t.receipt or t.repeated): return False
    return True

def evaluate(policy):
    cases = [{'track': t.track, 'task': t.name, 'expected': t.expected, 'actual': policy(t), 'passed': policy(t) == t.expected} for t in TASKS]
    return {'passed': sum(c['passed'] for c in cases), 'total': len(cases), 'by_track': {tr: sum(c['passed'] for c in cases if c['track']==tr) for tr in ['architecture','design','operations']}, 'cases': cases}

if __name__ == '__main__':
    report = {'dataset': 'OWL-SYNTHETIC-001', 'note': 'Tests deterministic policy logic, not model learning or real-world competence.', 'baseline': evaluate(baseline), 'guarded': evaluate(guarded)}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    assert report['guarded']['passed'] == 9
