FROM apache/airflow:3.3.0-python3.12

COPY --chown=airflow:root \
    docker/airflow/requirements.txt \
    /tmp/project-requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.3.0" \
    -r /tmp/project-requirements.txt