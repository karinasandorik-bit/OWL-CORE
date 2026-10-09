# OWL CRASH-RECOVERY-002

Local subprocess SIGKILL integration test. SQLite WAL synchronous=FULL durable outbox. Mock HTTP service supports deterministic event IDs and idempotent PUT. First worker is SIGKILLed after remote PUT but before local ack. Restart reconciles remote state and avoids duplicate PUT. A third invocation remains idempotent.

Run `cd experiments/crash_recovery_002 && python test_crash.py`.

**Limitations:** mock HTTP API is not GitHub, no live deployment, no concurrent workers, no real GitHub API kill point, no independently authenticated third-party evidence. This is a controlled failure-injection result, not production exactly-once proof. GitHub Contents API uses POST/PUT with different semantics and requires its own adapter and safe reconciliation.
