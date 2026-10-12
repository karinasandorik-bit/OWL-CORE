"""Run only on isolated PostgreSQL with OWL_TEST_DATABASE_URL set.
Requires: pip install 'psycopg[binary]' pytest
Setup: psql "$OWL_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f pg_worker/schema.sql
"""
import os
import uuid
import pytest
from worker import connect,enqueue,claim,complete,run_once

pytestmark=pytest.mark.skipif(not os.getenv("OWL_TEST_DATABASE_URL"),
                             reason="isolated PostgreSQL not configured")

def test_fencing_reclaim():
    with connect() as c:
        jid="test-"+str(uuid.uuid4())
        enqueue(c,jid,"healthcheck",{})
        first=claim(c,"worker-a",1)
        assert first["id"]==jid
        # Simulate expiry using a test-only DB update. Never run on production.
        c.execute("UPDATE owl_worker.jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE id=%s",(jid,))
        second=claim(c,"worker-b",30)
        assert second["id"]==jid
        assert second["fencing_token"]>first["fencing_token"]
        assert not complete(c,jid,"worker-a",first["fencing_token"],{"bad":True})
        assert complete(c,jid,"worker-b",second["fencing_token"],{"ok":True})

def test_idempotent_enqueue():
    with connect() as c:
        jid="test-"+str(uuid.uuid4())
        enqueue(c,jid,"healthcheck",{})
        enqueue(c,jid,"healthcheck",{"malicious":True})
        assert c.execute("SELECT count(*) AS n FROM owl_worker.jobs WHERE id=%s",(jid,)).fetchone()["n"]==1

def test_denied_capability():
    with connect() as c:
        with pytest.raises(ValueError,match="capability denied"):
            enqueue(c,"x","http_post",{})
