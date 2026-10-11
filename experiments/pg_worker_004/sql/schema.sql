CREATE SCHEMA IF NOT EXISTS owl_test;
CREATE TABLE IF NOT EXISTS owl_test.jobs (
 job_key text PRIMARY KEY, payload jsonb NOT NULL,
 state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','leased','done')),
 fence bigint NOT NULL DEFAULT 0, owner text, lease_until timestamptz,
 result jsonb, completed_at timestamptz, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS owl_test.effects (
 job_key text PRIMARY KEY REFERENCES owl_test.jobs(job_key),
 fence bigint NOT NULL, result jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
REVOKE ALL ON SCHEMA owl_test FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA owl_test FROM PUBLIC;
CREATE OR REPLACE FUNCTION owl_test.submit(p_key text,p_payload jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, owl_test AS $$
BEGIN
 INSERT INTO owl_test.jobs(job_key,payload) VALUES(p_key,p_payload) ON CONFLICT DO NOTHING;
 RETURN FOUND;
END $$;
CREATE OR REPLACE FUNCTION owl_test.claim(p_worker text,p_seconds int DEFAULT 10)
RETURNS TABLE(job_key text,payload jsonb,fence bigint) LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog,owl_test AS $$
BEGIN
 IF p_worker IS NULL OR length(p_worker)<1 OR p_seconds NOT BETWEEN 1 AND 300 THEN RAISE EXCEPTION 'invalid claim'; END IF;
 RETURN QUERY WITH candidate AS (
 SELECT j.job_key FROM owl_test.jobs j
 WHERE j.state='pending' OR (j.state='leased' AND j.lease_until < clock_timestamp())
 ORDER BY j.created_at,j.job_key FOR UPDATE SKIP LOCKED LIMIT 1
 ) UPDATE owl_test.jobs j SET state='leased',owner=p_worker,fence=j.fence+1,
 lease_until=clock_timestamp()+make_interval(secs=>p_seconds)
 FROM candidate c WHERE j.job_key=c.job_key
 RETURNING j.job_key,j.payload,j.fence;
END $$;
CREATE OR REPLACE FUNCTION owl_test.complete(p_key text,p_worker text,p_fence bigint,p_result jsonb)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog,owl_test AS $$
DECLARE n integer;
BEGIN
 IF p_result IS NULL THEN RETURN false; END IF;
 UPDATE owl_test.jobs SET state='done',result=p_result,completed_at=clock_timestamp(),lease_until=NULL
 WHERE job_key=p_key AND state='leased' AND owner=p_worker AND fence=p_fence
 AND lease_until > clock_timestamp();
 GET DIAGNOSTICS n=ROW_COUNT;
 IF n<>1 THEN RETURN false; END IF;
 INSERT INTO owl_test.effects(job_key,fence,result) VALUES(p_key,p_fence,p_result);
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION owl_test.receipt(p_key text)
RETURNS TABLE(job_key text,state text,fence bigint,result jsonb,effect_count bigint)
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog,owl_test AS $$
 SELECT j.job_key,j.state,j.fence,j.result,(SELECT count(*) FROM owl_test.effects e WHERE e.job_key=j.job_key)
 FROM owl_test.jobs j WHERE j.job_key=p_key
$$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA owl_test FROM PUBLIC;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='owl_test_worker') THEN CREATE ROLE owl_test_worker LOGIN; END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='owl_test_verifier') THEN CREATE ROLE owl_test_verifier LOGIN; END IF;
END $$;
GRANT USAGE ON SCHEMA owl_test TO owl_test_worker,owl_test_verifier;
GRANT EXECUTE ON FUNCTION owl_test.submit(text,jsonb),owl_test.claim(text,int),owl_test.complete(text,text,bigint,jsonb) TO owl_test_worker;
GRANT EXECUTE ON FUNCTION owl_test.receipt(text) TO owl_test_verifier;
REVOKE ALL ON ALL TABLES IN SCHEMA owl_test FROM owl_test_worker,owl_test_verifier;