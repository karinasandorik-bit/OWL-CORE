#!/usr/bin/env python3
"""Separate verifier process; consume JSON readback from stdin and fail closed."""
import hashlib,json,sys
d=json.load(sys.stdin)
expected="OWL-CORE|isolated|002"
assert d["job_key"]=="owl-core-test-002"
assert d["row_count"]==1
assert d["worker_id"]=="owl-core-python-worker-001"
assert d["input_sha256"]==hashlib.sha256(expected.encode()).hexdigest()
assert d["result"]["input"]==expected
assert d["result"]["output"]=="ACK:002"
assert d["result"]["status"]=="COMPLETED"
print(json.dumps({"verified":True,"job_key":d["job_key"]}))
