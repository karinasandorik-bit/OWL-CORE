"""Fail-closed unit checks for the production recovery candidate."""
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from sovereign.production_outbox import authorize, reconcile, execute_bounded, digest

class Cursor:
    def __init__(self, value): self.value=value
    def fetchone(self): return self.value

class FakeDB:
    def __init__(self, grant=None, outbox=None):
        self.grant=grant
        self.outbox=outbox
        self.events=[]
    def execute(self, sql, params=()):
        self.events.append((sql,params))
        if "FROM public.owl_capability_grants" in sql: return Cursor(self.grant)
        if "FROM owl_production_outbox" in sql: return Cursor(self.outbox)
        return Cursor(None)
    def commit(self): self.events.append(("commit",()))

class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.repo="karinasandorik-bit/OWL-CORE"
        self.branch="owl/revenue/canary"
        self.path="owl/revenue/proof.json"
        self.payload=b'{"proof":true}\n'
        self.sha=digest(self.payload)
        self.grant=(True,datetime.now(timezone.utc)+timedelta(hours=1),None,
                    "github_draft_artifact",
                    {"repository":self.repo,"branch_prefix":"owl/revenue/","max_actions":1})
        self.outbox=(self.sha,self.repo,self.branch,self.path,"pending",None)
    def test_missing_grant(self):
        with self.assertRaisesRegex(PermissionError,"GRANT_MISSING"):
            authorize(FakeDB(), "grant", self.repo, self.branch)
    def test_revoked_grant(self):
        g=list(self.grant);g[2]=datetime.now(timezone.utc)
        with self.assertRaisesRegex(PermissionError,"GRANT_DENIED"):
            authorize(FakeDB(grant=tuple(g)),"grant",self.repo,self.branch)
    def test_expired_grant(self):
        g=list(self.grant);g[1]=datetime.now(timezone.utc)-timedelta(seconds=1)
        with self.assertRaises(PermissionError):
            authorize(FakeDB(grant=tuple(g)),"grant",self.repo,self.branch)
    def test_wrong_branch(self):
        with self.assertRaises(PermissionError):
            authorize(FakeDB(grant=self.grant),"grant",self.repo,"main")
    def test_unbounded_grant(self):
        g=list(self.grant);g[4]={**g[4],"max_actions":2}
        with self.assertRaises(PermissionError):
            authorize(FakeDB(grant=tuple(g)),"grant",self.repo,self.branch)
    def test_missing_remote_is_pending(self):
        result=reconcile(FakeDB(outbox=self.outbox),"op",self.sha,lambda *args:None)
        self.assertEqual(result["outcome"],"PENDING")
    def test_verified_remote(self):
        result=reconcile(FakeDB(outbox=self.outbox),"op",self.sha,
                         lambda *args:(self.payload,"blob","commit",1))
        self.assertEqual((result["outcome"],result["commit_sha"]),("VERIFIED","commit"))
    def test_duplicate_remote_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"REMOTE_TAINT_OR_DUPLICATE"):
            reconcile(FakeDB(outbox=self.outbox),"op",self.sha,
                      lambda *args:(self.payload,"blob","commit",2))
    def test_content_tamper_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"REMOTE_TAINT_OR_DUPLICATE"):
            reconcile(FakeDB(outbox=self.outbox),"op",self.sha,
                      lambda *args:(b"evil","blob","commit",1))
    def test_outbox_tamper_rejected(self):
        bad=("incorrect",self.repo,self.branch,self.path,"pending",None)
        with self.assertRaisesRegex(RuntimeError,"MISSING_OR_TAINTED_OUTBOX"):
            reconcile(FakeDB(outbox=bad),"op",self.sha,lambda *args:None)
    def test_unconfigured_actuator_has_no_effect(self):
        called=[]
        with self.assertRaisesRegex(PermissionError,"ACTUATOR_DISABLED"):
            execute_bounded(FakeDB(),operation_id="op",grant_id="grant",
                repo=self.repo,branch=self.branch,path=self.path,payload=self.payload,
                read_remote=lambda *args:called.append("read"),
                create_remote=lambda *args:called.append("write"),enabled=False)
        self.assertEqual(called,[])

if __name__=="__main__": unittest.main()
