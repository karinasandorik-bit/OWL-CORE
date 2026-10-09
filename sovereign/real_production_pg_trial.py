"""Isolated real PostgreSQL + GitHub Contents crash/recovery acceptance trial.

This test NEVER contacts production DB. A per-run GitHub branch and canary path
are used; credentials are short-lived GITHUB_TOKEN scoped to this CI workflow.
"""
import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.types.json import Jsonb
from sovereign.production_outbox import SCHEMA, digest, execute_bounded, reconcile

REPO = os.environ["GITHUB_REPOSITORY"]
RUN = os.environ["GITHUB_RUN_ID"]
TOKEN = os.environ["GITHUB_TOKEN"]
DSN = os.environ["DATABASE_URL"]
BASE = os.environ["GITHUB_SHA"]
BRANCH = "owl/revenue/pg-recovery-" + RUN
PATH = "owl/revenue/pg-recovery-" + RUN + ".json"
OP = "owl:production-integration:" + RUN
GRANT = "OWL-CI-ONE-SHOT-" + RUN
DATA = (json.dumps({"schema": "OWL_PG_RECOVERY_TEST_V1", "run": RUN, "operation_id": OP},
                   sort_keys=True) + "\n").encode()
SHA = digest(DATA)

def github(method, route, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": "Bearer " + TOKEN,
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request("https://api.github.com" + route,
                                     data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=35) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 404, None
        raise RuntimeError("GITHUB_HTTP_" + str(exc.code)) from exc

def encoded_path():
    return urllib.parse.quote(PATH, safe="/")

def read_remote(repo, branch, path):
    assert (repo, branch, path) == (REPO, BRANCH, PATH), "SCOPE_MISMATCH"
    status, obj = github("GET", f"/repos/{REPO}/contents/{encoded_path()}?ref={BRANCH}")
    if status == 404:
        return None
    raw = base64.b64decode(obj["content"])
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != obj["sha"]:
        raise RuntimeError("INDEPENDENT_GIT_BLOB_SHA_MISMATCH")
    _, commits = github(
        "GET", f"/repos/{REPO}/commits?sha={BRANCH}&path={encoded_path()}&per_page=100")
    if not isinstance(commits, list):
        raise RuntimeError("COMMIT_HISTORY_UNREADABLE")
    remote_commit = commits[0]["sha"] if commits else None
    return raw, blob, remote_commit, len(commits)

def create_remote(repo, branch, path, raw):
    assert (repo, branch, path) == (REPO, BRANCH, PATH), "SCOPE_MISMATCH"
    status, obj = github("PUT", f"/repos/{REPO}/contents/{encoded_path()}", {
        "message": "owl integration canary " + RUN,
        "content": base64.b64encode(raw).decode(),
        "branch": BRANCH,
    })
    if status not in (200, 201) or not obj.get("commit", {}).get("sha"):
        raise RuntimeError("GITHUB_WRITE_NOT_ACKNOWLEDGED")
    if os.environ.get("OWL_KILL_AFTER_WRITE") == "1":
        print("GITHUB_WRITE_ACKNOWLEDGED_THEN_SIGKILL commit=" + obj["commit"]["sha"],
              flush=True)
        os.kill(os.getpid(), signal.SIGKILL)

def ensure_branch():
    status, current = github("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    if status == 404:
        code, _ = github("POST", f"/repos/{REPO}/git/refs", {
            "ref": "refs/heads/" + BRANCH,
            "sha": BASE
        })
        if code != 201:
            raise RuntimeError("BRANCH_CREATE_FAILED")
    elif current["object"]["sha"] != BASE:
        raise RuntimeError("TEST_BRANCH_EXISTS_DIFFERENT_BASE")
    if read_remote(REPO, BRANCH, PATH) is not None:
        raise RuntimeError("TEST_ARTIFACT_ALREADY_EXISTS")

def prepare():
    with psycopg.connect(DSN) as db:
        db.execute(SCHEMA)
        db.execute("""CREATE TABLE IF NOT EXISTS public.owl_capability_grants (
            grant_id text PRIMARY KEY, enabled boolean NOT NULL, expires_at timestamptz,
            revoked_at timestamptz, actuator text NOT NULL, scope jsonb NOT NULL
        )""")
        db.execute("""INSERT INTO public.owl_capability_grants
            (grant_id, enabled, expires_at, revoked_at, actuator, scope)
            VALUES (%s, true, %s, NULL, 'github_draft_artifact', %s)""",
            (GRANT, datetime.now(timezone.utc) + timedelta(minutes=20),
             Jsonb({"repository": REPO, "branch_prefix": "owl/revenue/", "max_actions": 1})))
        db.commit()

def worker():
    with psycopg.connect(DSN) as db:
        result = execute_bounded(
            db, operation_id=OP, grant_id=GRANT, repo=REPO,
            branch=BRANCH, path=PATH, payload=DATA,
            read_remote=read_remote, create_remote=create_remote, enabled=True)
        print("WORKER_VERIFIED " + result["blob_sha"], flush=True)
        return result

def main():
    ensure_branch()
    prepare()
    if os.environ.get("OWL_CHILD_WORKER") == "1":
        worker()
        return
    child_env = {**os.environ, "OWL_CHILD_WORKER": "1",
                 "OWL_KILL_AFTER_WRITE": "1", "OWL_ENABLE_GITHUB_ACTUATOR": "1"}
    first = subprocess.run([sys.executable, "-m",
                            "sovereign.real_production_pg_trial"],
                           env=child_env, capture_output=True, text=True, timeout=120)
    print("first_exit=" + str(first.returncode) + " " + first.stdout.strip(), flush=True)
    if first.returncode != -signal.SIGKILL or (
            "GITHUB_WRITE_ACKNOWLEDGED_THEN_SIGKILL" not in first.stdout):
        raise RuntimeError("NO_PROVEN_EXTERNAL_WRITE_THEN_SIGKILL")
    with psycopg.connect(DSN) as db:
        row = db.execute("""SELECT state,attempts FROM owl_production_outbox
                            WHERE operation_id=%s""", (OP,)).fetchone()
        if row != ("pending", 1):
            raise RuntimeError("NO_DURABLE_PENDING " + str(row))
    os.environ["OWL_ENABLE_GITHUB_ACTUATOR"] = "1"
    os.environ.pop("OWL_KILL_AFTER_WRITE", None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result(timeout=120) for future in futures]
    if len(results) != 2 or any(r["outcome"] != "VERIFIED" for r in results):
        raise RuntimeError("CONCURRENT_RECOVERY_FAILED")
    remote = read_remote(REPO, BRANCH, PATH)
    if remote is None or remote[0] != DATA or remote[3] != 1:
        raise RuntimeError("REMOTE_EFFECT_NOT_EXACTLY_ONCE")
    with psycopg.connect(DSN) as db:
        row = db.execute("""SELECT state,attempts,remote_blob_sha,remote_commit_sha
                            FROM owl_production_outbox WHERE operation_id=%s""",
                         (OP,)).fetchone()
        if row != ("verified", 3, remote[1], remote[2]):
            raise RuntimeError("OUTBOX_LEDGER_REMOTE_MISMATCH " + str(row))
        result = reconcile(db, OP, SHA, read_remote)
        if result["outcome"] != "VERIFIED":
            raise RuntimeError("INDEPENDENT_RECONCILE_FAILED")
        grant_count = db.execute(
            "SELECT count(*) FROM public.owl_capability_grants WHERE grant_id=%s",
            (GRANT,)).fetchone()[0]
        outbox_count = db.execute(
            "SELECT count(*) FROM owl_production_outbox WHERE operation_id=%s",
            (OP,)).fetchone()[0]
        if (grant_count, outbox_count) != (1, 1):
            raise RuntimeError("DUPLICATE_DB_ROWS")
    print("OWL_PRODUCTION_PG_RECOVERED " +
          json.dumps({"operation_id": OP, "first_exit": first.returncode,
                      "recovery_workers": 2, "attempts": row[1],
                      "outbox_state": row[0], "path_commits": remote[3],
                      "remote_commit_sha": remote[2], "git_blob_sha": remote[1],
                      "payload_sha256": SHA}, sort_keys=True), flush=True)
    print("PRODUCTION_PG_INTEGRATION_PASS", flush=True)

if __name__ == "__main__":
    main()
