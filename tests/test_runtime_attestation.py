import os,tempfile,sqlite3,unittest
from unittest.mock import patch
from runtime_attestation import attest
class AttestationTests(unittest.TestCase):
 def test_bounded_readonly_attestation(self):
  with tempfile.TemporaryDirectory() as td:
   db=td+"/owl.db"
   sqlite3.connect(db).close()
   with patch.dict(os.environ,{"OWL_DB":db,"RAILWAY_DEPLOYMENT_ID":"deploy-test","RAILWAY_GIT_COMMIT_SHA":"a"*40}):
    result=attest()
   self.assertTrue(result["verified"])
   self.assertEqual(result["identity"]["deployment_id"],"deploy-test")
 def test_missing_database_fails_closed(self):
  with patch.dict(os.environ,{"OWL_DB":"/nonexistent/absent.db"}):
   self.assertFalse(attest()["verified"])
if __name__=="__main__":unittest.main()
