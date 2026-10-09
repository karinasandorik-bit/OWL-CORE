import os
import tempfile
import unittest
import worker

class WorkerTests(unittest.TestCase):
    def test_idempotent_and_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            worker.DB = os.path.join(folder, "test.db")
            db = worker.connect()
            worker.enqueue(db, "job-1", "healthcheck", {})
            worker.enqueue(db, "job-1", "healthcheck", {})
            self.assertEqual(db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)
            self.assertTrue(worker.run_once(db)["result"]["ok"])
            self.assertIsNone(worker.run_once(db))
            with self.assertRaises(ValueError):
                worker.enqueue(db, "bad", "transfer", {})
if __name__ == "__main__":
    unittest.main()
