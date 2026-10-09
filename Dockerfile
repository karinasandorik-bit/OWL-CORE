FROM python:3.12-slim
WORKDIR /app
COPY worker.py runtime.py recovery_verifier.py runtime_attestation.py runtime_reconcile.py ./
ENV PYTHONUNBUFFERED=1 OWL_DB=/data/owl_jobs.sqlite3 OWL_POLL_SECONDS=10
RUN mkdir -p /data
CMD ["python", "runtime.py"]
