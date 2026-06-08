FROM apache/superset:3.1.0

USER root
RUN pip install --no-cache-dir psycopg2-binary
COPY superset_config.py /app/pythonpath/superset_config.py
USER superset
