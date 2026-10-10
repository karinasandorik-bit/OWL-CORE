-- Review only: not applied to Supabase
ALTER TABLE owl_core.execution_jobs DROP CONSTRAINT IF EXISTS execution_jobs_state_check;
ALTER TABLE owl_core.execution_jobs ADD CONSTRAINT execution_jobs_state_check
 CHECK(state IN ('proposed','authorized','running','recovering','executed','verified','rejected','needs_review','failed'));
CREATE INDEX IF NOT EXISTS owl_execution_claim_idx ON owl_core.execution_jobs(state,lease_until,created_at);
