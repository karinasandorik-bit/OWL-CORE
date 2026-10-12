"""Negative and boundary tests for the remote single-run evidence verifier.

Fixture is intentionally synthetic. Passing these tests never means that
an actual remote GitHub timeout was performed.
"""
from copy import deepcopy
from remote_proof_verifier import verify,ORDER

def sample():
    trial="owl-remote-fixture-001";ref="refs/heads/owl-proof/fixture";sha="a"*40
    events=[{"type":t,"trial_id":trial,"run_id":"fixture-only","receipt_url":"https://example.invalid/fixture"} for t in ORDER]
    by={e["type"]:e for e in events}
    by["remote_commit"].update(provider="github.com",http_status=201,ref=ref,sha=sha)
    by["response_drop"].update(upstream_http_status=201,downstream_bytes=0)
    by["worker_a_sigkill"].update(pid=100,exit_signal="SIGKILL",fencing_token=1)
    by["lease_takeover"].update(pid=101,expired_lease=True,fencing_token=2)
    by["github_get"].update(ref=ref,sha=sha)
    by["postgres_readback"].update(trial_id=trial,ref=ref,sha=sha)
    by["duplicate_rejection"].update(http_status=422,ref=ref)
    by["provider_readback"].update(provider="github.com",ref=ref,sha=sha,exact_ref_count=1)
    return {"trial_id":trial,"events":events}

def test_structural_fixture_passes_only_schema_not_authenticity():
    # Synthetic fixture tests internal consistency, NOT genuine receipts.
    assert verify(sample())[0]

def test_drop_missing_fails_closed():
    x=sample();x["events"][1]["downstream_bytes"]=2
    assert not verify(x)[0]

def test_pid_reuse_fails_closed():
    x=sample();x["events"][3]["pid"]=100
    assert not verify(x)[0]

def test_wrong_external_effect_count_fails_closed():
    x=sample();x["events"][-1]["exact_ref_count"]=2
    assert not verify(x)[0]

def test_multiple_ci_runs_fails_closed():
    x=sample();x["events"][-1]["run_id"]="other-run"
    assert not verify(x)[0]

def test_missing_remote_commit_fails_closed():
    x=sample();x["events"].pop(0)
    assert not verify(x)[0]

def test_wrong_trial_id_fails_closed():
    x=sample();x["events"][2]["trial_id"]="different"
    assert not verify(x)[0]

def test_no_receipt_fails_closed():
    x=sample();x["events"][4].pop("receipt_url")
    assert not verify(x)[0]
