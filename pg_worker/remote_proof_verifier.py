"""Independent acceptance gate for a single remote HTTP fault-injection CI run.

Never substitutes synthetic results for real GitHub receipts. Only accepts an
evidence bundle whose source and fields can be independently audited.
"""
import json
from pathlib import Path

ORDER = ("remote_commit", "response_drop", "worker_a_sigkill",
         "lease_takeover", "github_get", "postgres_readback",
         "duplicate_rejection", "provider_readback")

def verify(bundle):
    problems=[]
    trial=bundle.get("trial_id")
    events=bundle.get("events")
    if not isinstance(trial,str) or not trial.startswith("owl-remote-"):
        problems.append("missing stable trial_id")
    if not isinstance(events,list):
        return False,problems+["missing event journal"]
    types=[e.get("type") for e in events if isinstance(e,dict)]
    if types!=list(ORDER):
        problems.append("missing or unordered required events")
    for e in events:
        if not isinstance(e,dict) or e.get("trial_id")!=trial:
            problems.append("event trial_id mismatch")
            break
    by_type={e.get("type"):e for e in events if isinstance(e,dict)}
    a=by_type.get("worker_a_sigkill",{})
    b=by_type.get("lease_takeover",{})
    commit=by_type.get("remote_commit",{})
    drop=by_type.get("response_drop",{})
    github=by_type.get("github_get",{})
    postgres=by_type.get("postgres_readback",{})
    duplicate=by_type.get("duplicate_rejection",{})
    provider=by_type.get("provider_readback",{})
    if not a.get("pid") or not b.get("pid") or a.get("pid")==b.get("pid"):
        problems.append("two distinct process IDs are required")
    if a.get("exit_signal")!="SIGKILL":
        problems.append("worker A SIGKILL not proven")
    if commit.get("provider")!="github.com" or commit.get("http_status")!=201:
        problems.append("remote GitHub HTTP 201 evidence missing")
    if drop.get("upstream_http_status")!=201 or drop.get("downstream_bytes")!=0:
        problems.append("response drop after upstream commit not proven")
    if not b.get("expired_lease") or b.get("fencing_token",0)<=a.get("fencing_token",0):
        problems.append("lease expiry and fencing promotion not proven")
    ref=commit.get("ref")
    sha=commit.get("sha")
    if not isinstance(ref,str) or not ref.startswith("refs/heads/owl-proof/"):
        problems.append("non-isolated remote ref")
    if not sha or github.get("ref")!=ref or github.get("sha")!=sha:
        problems.append("remote ref GET readback mismatch")
    if postgres.get("trial_id")!=trial or postgres.get("ref")!=ref or postgres.get("sha")!=sha:
        problems.append("PostgreSQL readback mismatch")
    if provider.get("provider")!="github.com" or provider.get("ref")!=ref or provider.get("sha")!=sha or provider.get("exact_ref_count")!=1:
        problems.append("external provider readback missing or duplicate detected")
    if duplicate.get("http_status")!=422 or duplicate.get("ref")!=ref:
        problems.append("remote duplicate rejection absent")
    if any(not e.get("receipt_url") for e in events if isinstance(e,dict)):
        problems.append("receipt URLs missing")
    if len({e.get("run_id") for e in events if isinstance(e,dict)})!=1 or not events or not events[0].get("run_id"):
        problems.append("evidence spans multiple or unspecified CI runs")
    return not problems,problems

def main():
    import sys
    data=json.loads(Path(sys.argv[1]).read_text())
    ok,problems=verify(data)
    print(json.dumps({"verdict":"PROVEN" if ok else "NOT_PROVEN","issues":problems}))
    raise SystemExit(0 if ok else 1)

if __name__=="__main__":main()
