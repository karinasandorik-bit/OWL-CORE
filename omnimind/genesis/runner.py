"""OWL Genesis deterministic task runner. Does not execute arbitrary user code.
Run: python3 -m unittest discover -s tests
"""
from dataclasses import dataclass
import hashlib, json
@dataclass(frozen=True)
class Case:
    value: str
    expected: bool

def baseline(value: str) -> bool:
    return "@" in value

def candidate(value: str) -> bool:
    # syntactic check only; not a guarantee of real email deliverability
    parts = value.split("@")
    return len(parts)==2 and bool(parts[0]) and "." in parts[1] and all(parts[1].split("."))

def evaluate(method, cases):
    return {"passed":sum(method(c.value)==c.expected for c in cases),"total":len(cases)}

def digest_cases(cases):
    payload=json.dumps([c.__dict__ for c in cases],sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()

HOLDOUT=(
 Case("person@example.org",True),Case("bad@",False),Case("x@site.co",True),
 Case("not-an-email",False),Case("@site.co",False),Case("a@b",False))
