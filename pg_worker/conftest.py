"""CI-only isolation: OWL_TEST_DATABASE_URL must point to disposable test DB."""
import os
import pytest
import psycopg

@pytest.fixture(autouse=True)
def clean_isolated_queue():
    url=os.environ.get("OWL_TEST_DATABASE_URL")
    if not url:
        yield
        return
    # Fail closed against accidental production connections.
    assert "owl_test" in url and "localhost" in url, "refusing non-isolated database"
    with psycopg.connect(url,autocommit=True) as conn:
        conn.execute("DELETE FROM owl_worker.effect_outbox")
        conn.execute("DELETE FROM owl_worker.jobs")
    yield
