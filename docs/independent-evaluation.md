# OWL independent evaluator (phase 2)

Boundary: existing `runtime.py` calls `worker.run_once`; `evaluate_candidate` creates an idempotent SQLite `evaluation_outbox` item and returns **PENDING**, never approval. A **separate, operator-controlled judge process** reads outbox data read-only, grades predictions against fixture labels that are *not committed*, and writes a PostgreSQL event.

## Deploy prerequisites (NOT deployed by this PR)

1. In PostgreSQL, run `sql/evolution_ledger.sql` as schema owner. Provision distinct `owl_judge` account with only `SELECT, INSERT` on ledger table, no schema ownership or DDL. DB admins remain trusted: this is append-only for unprivileged roles, **not cryptographically immutable**.
2. Provision independent judge runtime with `pip install "psycopg[binary]>=3,<4"`, `OWL_JUDGE_DATABASE_URL` (secret), mount worker SQLite database **read-only**, and mount private fixture JSON *outside repo and worker environment*. A SQLite DB inside an ephemeral container will not create a durable production handoff: a persistent shared volume/queue or Postgres outbox migration is required before deployment across hosts.
3. Fixture JSON: `{"dataset_id":"heldout-v1","cases":[{"id":"a","expected":true},{"id":"b","expected":false}]}`. Case IDs may be published to the worker; expected labels **must not**. Enforce disjoint train/test data and dataset rotation. Holding labels alone does not prove real-world generalization.
4. Submit bounded request through current worker `python worker.py enqueue request-001 evaluate_candidate '{"dataset_id":"heldout-v1","candidate_id":"c1","baseline_id":"b1","candidate_predictions":{"a":true,"b":false},"baseline_predictions":{"a":false,"b":false}}'`; then run the current worker once. Independently execute `python independent_judge.py --worker-db /readonly/owl_jobs.sqlite3 --heldout /secrets/heldout.json`.
5. Validate `SELECT request_id,request_hash,verdict FROM owl_evaluation_events` using a separate read-only auditor, then rerun judge: no duplicate rows. Test altered same-ID requests; judge fails closed. Back up WAL / anchor hashes to independent storage to address privileged rewrites.

No promotion/deploy keys are used by the judge. Any later promotion requires a separate authority process and independently validated test protocol. No exchange, wallet, payment, or signer permissions are introduced.

## Invariants / limitations

- Worker never sees hidden outcomes or PostgreSQL credentials.
- Worker can only enqueue: it cannot set `promotion_authorized=true`.
- Judge validates exact prediction coverage, writes a durable verdict transactionally, and detects inconsistent repeat ID.
- PostgreSQL event INSERT and SQLite outbox are **not** a distributed transaction; retries are deduplicated by PostgreSQL unique request ID and request hash.
- Existing historical `evaluate_candidate` job semantics change from immediate rejection to pending external review, and existing successful SIGKILL recovery jobs stay unchanged.
- Do not merge/deploy without independently reviewing fixture secrecy, SQLite volume topology, DB role permissions, recovery under crash, and GitHub checks.
