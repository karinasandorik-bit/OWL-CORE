FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir 'psycopg[binary]==3.2.10'
COPY worker.py runtime.py recovery_verifier.py revenue_actuator.py ./
ENV PYTHONUNBUFFERED=1 OWL_DB=/data/owl_jobs.sqlite3 OWL_POLL_SECONDS=10
RUN mkdir -p /data
CMD ["python", "runtime.py"]
