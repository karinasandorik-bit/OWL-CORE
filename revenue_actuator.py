"""Opt-in, fail-closed GitHub artifact actuator. Never runs without dedicated credentials."""
import hashlib
import json
import os
import urllib.error
import urllib.request

GRANT = "OWL-REVENUE-WORKER-001"
WORKER = "owl-worker"
REPO = "karinasandorik-bit/OWL-CORE"
BRANCH = "owl/revenue/authority-001"
PATH = "evidence/OWL-REVENUE-WORKER-001-CANARY.json"

def _github(method, url, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "owl-revenue-canary/1",
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)

def execute_once():
    if os.getenv("OWL_REVENUE_ENABLED") != "1":
        return {"status": "disabled"}
    # DB credentials must be restricted to the grant RPC and append-only event operations.
    dsn = os.environ["OWL_AUTHORITY_DSN"]
    token = os.environ["OWL_GITHUB_FINE_GRAINED_TOKEN"]
    import psycopg
    import base64
    artifact = json.dumps({"trial":"OWL-REVENUE-WORKER-001","purpose":"bounded_canary","payment":False},sort_keys=True,separators=(",",":")).encode()
    digest = hashlib.sha256(artifact).hexdigest()
    with psycopg.connect(dsn, connect_timeout=10) as db:
        with db.transaction():
            action_id, replay = db.execute(
                "select action_id,already_reserved from public.owl_reserve_github_artifact(%s,%s,%s,%s,%s,%s)",
                (GRANT,WORKER,REPO,BRANCH,PATH,digest)
            ).fetchone()
        # Independent readback BEFORE any write makes crash after GitHub success recoverable.
        url = f"https://api.github.com/repos/{REPO}/contents/{PATH}?ref={BRANCH}"
        try:
            remote = _github("GET",url,token)
        except urllib.error.HTTPError as exc:
            if exc.code != 404: raise
            remote = None
        if remote:
            actual = base64.b64decode(remote["content"].replace("\n",""))
            if hashlib.sha256(actual).hexdigest() != digest:
                raise RuntimeError("OWL_CONFLICT_REMOTE_CONTENT")
            commit_sha = remote.get("sha")  # blob SHA, NOT commit SHA
            status = "already_present"
        else:
            if replay:
                # Uncertain prior result: do not create another commit.
                raise RuntimeError("OWL_REPLAY_REQUIRES_INDEPENDENT_VERIFICATION")
            result = _github("PUT",f"https://api.github.com/repos/{REPO}/contents/{PATH}",token,{
                "message":"OWL revenue bounded canary",
                "branch":BRANCH,
                "content":base64.b64encode(artifact).decode(),
            })
            commit_sha = result["commit"]["sha"]
            status = "created"
        # Store evidence as append-only events; verified only after independent verifier checks GitHub commit.
        with db.transaction():
            db.execute("insert into public.owl_action_events(action_id,event_type,payload) values(%s,%s,%s::jsonb)",
                       (action_id,"GITHUB_WRITE_OBSERVED",json.dumps({"status":status,"sha":commit_sha,"payload_sha256":digest})))
    return {"action_id":action_id,"status":status,"sha":commit_sha}

if __name__ == "__main__":
    print(json.dumps(execute_once()))
