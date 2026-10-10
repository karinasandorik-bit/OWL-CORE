"""Fail-closed reconciliation of runtime attestation and Railway API observation."""
import re
SHA=re.compile(r"^[0-9a-f]{40}$")
def reconcile(attestation,railway,expected_commit):
    identity=attestation.get("identity",{})
    checks=attestation.get("checks",{})
    if not attestation.get("verified") or not all(checks.get(k) is True for k in ("arithmetic","sqlite_readonly")):
        return {"verdict":"UNVERIFIED","reason":"runtime_checks_failed"}
    deployment_id=identity.get("deployment_id")
    commit=identity.get("commit_sha")
    if not deployment_id or not commit or not SHA.fullmatch(commit):
        return {"verdict":"UNVERIFIED","reason":"missing_runtime_identity"}
    if railway.get("id")!=deployment_id or railway.get("status")!="SUCCESS":
        return {"verdict":"UNVERIFIED","reason":"railway_deployment_mismatch"}
    if railway.get("meta",{}).get("commitHash")!=commit:
        return {"verdict":"UNVERIFIED","reason":"railway_commit_mismatch"}
    if commit!=expected_commit:
        return {"verdict":"ROLLBACK_REQUIRED","reason":"unexpected_commit","observed_commit":commit}
    return {"verdict":"RECOVERED_CANDIDATE","deployment_id":deployment_id,"commit_sha":commit}
