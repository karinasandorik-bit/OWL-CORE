"""Production candidate: fail-closed PostgreSQL outbox with independent remote verification.

No caller in runtime.py is authorized to execute an external write. The execution
function requires explicit invocation, a valid scoped authority row, and a flag.
"""
import contextlib
import hashlib
import json
import os
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS owl_production_outbox (
 operation_id text PRIMARY KEY, grant_id text NOT NULL UNIQUE, request_sha256 text NOT NULL,
 target_repo text NOT NULL, target_branch text NOT NULL, target_path text NOT NULL, state text NOT NULL
 CHECK (state IN ('pending','verified','blocked')),
 attempts integer NOT NULL DEFAULT 0, remote_blob_sha text,
 remote_commit_sha text, updated_at timestamptz NOT NULL DEFAULT now()
);
"""

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def authorize(db, grant_id, repo, branch):
    """Deny when authority table, grant, scope, or time constraints are unavailable."""
    row = db.execute(
        """SELECT enabled, expires_at, revoked_at, actuator, scope
           FROM public.owl_capability_grants WHERE grant_id=%s""", (grant_id,)
    ).fetchone()
    if not row:
        raise PermissionError("GRANT_MISSING")
    enabled, expires, revoked, actuator, scope = row
    scope = scope if isinstance(scope, dict) else json.loads(scope)
    if (not enabled or revoked is not None or expires is None or
        expires <= datetime.now(timezone.utc) or actuator != "github_draft_artifact" or
        scope.get("repository") != repo or
        not branch.startswith(scope.get("branch_prefix", "owl/revenue/"))):
        raise PermissionError("GRANT_DENIED")
    if scope.get("max_actions") != 1:
        raise PermissionError("UNBOUNDED_GRANT")
    return True

def reconcile(db, op, expected_sha256, read_remote):
    """Read-only check: remote result does not imply local authorization."""
    row = db.execute(
        """SELECT request_sha256,target_repo,target_branch,target_path,state,remote_blob_sha
           FROM owl_production_outbox WHERE operation_id=%s""", (op,)
    ).fetchone()
    if not row or row[0] != expected_sha256:
        raise RuntimeError("MISSING_OR_TAINTED_OUTBOX")
    actual = read_remote(row[1], row[2], row[3])  # returns (bytes, blob_sha, commit_sha, path_commit_count)
    if actual is None:
        return {"outcome": "PENDING", "operation_id": op}
    raw, blob_sha, commit_sha, count = actual
    if digest(raw) != expected_sha256 or count != 1 or not blob_sha or not commit_sha:
        raise RuntimeError("REMOTE_TAINT_OR_DUPLICATE")
    if row[5] is not None and row[5] != blob_sha:
        raise RuntimeError("REMOTE_CHANGED")
    return {"outcome": "VERIFIED", "operation_id": op,
            "blob_sha": blob_sha, "commit_sha": commit_sha}

def execute_bounded(db, *, operation_id, grant_id, repo, branch, path, payload,
                    read_remote, create_remote, enabled=False):
    """Manual opt-in only; production runtime never calls this function.

    read_remote(repo, branch, path) returns bytes/blob SHA/commit SHA/path commit count, or None.
    create_remote must create ONLY this exact path in this repo and branch.
    """
    if not enabled or os.environ.get("OWL_ENABLE_GITHUB_ACTUATOR") != "1":
        raise PermissionError("ACTUATOR_DISABLED")
    if not operation_id or not branch.startswith("owl/revenue/") or not path.startswith("owl/revenue/"):
        raise PermissionError("OUT_OF_SCOPE")
    # One PG session advisory lock is retained across the external operation.
    db.execute("SELECT pg_advisory_lock(hashtext(%s))", (operation_id,))
    try:
        authorize(db, grant_id, repo, branch)
        sha = digest(payload)
        db.execute(
            """INSERT INTO owl_production_outbox
                 (operation_id,grant_id,request_sha256,target_repo,target_branch,target_path,state)
               VALUES (%s,%s,%s,%s,%s,%s,'pending') ON CONFLICT DO NOTHING""",
            (operation_id, grant_id, sha, repo, branch, path))
        db.commit()
        row = db.execute(
            """SELECT grant_id,request_sha256,target_repo,target_branch,target_path,state
               FROM owl_production_outbox WHERE operation_id=%s""", (operation_id,)
        ).fetchone()
        if not row or row[:5] != (grant_id, sha, repo, branch, path) or row[5] == "blocked":
            raise RuntimeError("OUTBOX_CONFLICT")
        db.execute("UPDATE owl_production_outbox SET attempts=attempts+1 WHERE operation_id=%s",
                   (operation_id,))
        db.commit()
        result = reconcile(db, operation_id, sha, read_remote)
        if result["outcome"] == "PENDING":
            # Re-check grant immediately before any external effect.
            authorize(db, grant_id, repo, branch)
            create_remote(repo, branch, path, payload)
            # If process dies here, retry observes remote instead of re-creating.
            result = reconcile(db, operation_id, sha, read_remote)
        if result["outcome"] != "VERIFIED":
            raise RuntimeError("EXTERNAL_EFFECT_NOT_VERIFIED")
        db.execute(
            """UPDATE owl_production_outbox SET state='verified',
               remote_blob_sha=%s,remote_commit_sha=%s,updated_at=now()
               WHERE operation_id=%s AND state='pending'""",
            (result["blob_sha"], result["commit_sha"], operation_id))
        db.commit()
        return result
    finally:
        db.execute("SELECT pg_advisory_unlock(hashtext(%s))", (operation_id,))
