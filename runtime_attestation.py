"""Read-only runtime identity and bounded self-test. No secrets or privileged API."""
import hashlib,json,os,sqlite3
from pathlib import Path

def attest():
    db_path=os.environ.get("OWL_DB","/data/owl_jobs.sqlite3")
    identity={"deployment_id":os.environ.get("RAILWAY_DEPLOYMENT_ID"),
              "commit_sha":os.environ.get("RAILWAY_GIT_COMMIT_SHA"),
              "service_id":os.environ.get("RAILWAY_SERVICE_ID"),
              "environment_id":os.environ.get("RAILWAY_ENVIRONMENT_ID")}
    checks={"arithmetic":sum([2,3,5])==10,"sqlite_readonly":False}
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro",uri=True,timeout=2) as conn:
            checks["sqlite_readonly"]=conn.execute("PRAGMA quick_check").fetchone()[0]=="ok"
    except (sqlite3.Error,OSError):pass
    return {"schema":"OWL_RUNTIME_ATTESTATION_V1","identity":identity,
            "checks":checks,"verified":all(checks.values()),
            "code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
if __name__=="__main__":
    print(json.dumps(attest(),sort_keys=True))
