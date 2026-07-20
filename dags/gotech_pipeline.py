"""Airflow DAG for the complete GoTech data pipeline."""

from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG


PROJECT_DIRECTORY = "/opt/airflow/project"


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}


with DAG(
    dag_id="gotech_bronze_silver_gold",
    description=(
        "Pipeline completo desde CSV Raw hasta "
        "tablas analíticas Gold en PostgreSQL."
    ),
    default_args=default_args,
    schedule=None,
    start_date=pendulum.datetime(
        2026,
        7,
        1,
        tz="America/La_Paz",
    ),
    catchup=False,
    max_active_runs=1,
    tags=[
        "bootcamp",
        "data-engineering",
        "bronze",
        "silver",
        "gold",
    ],
) as dag:

    build_bronze = BashOperator(
        task_id="build_bronze",
        bash_command=(
            "python -m src.ingestion.bronze"
        ),
        cwd=PROJECT_DIRECTORY,
    )

    build_and_validate_silver = BashOperator(
        task_id="build_and_validate_silver",
        bash_command=(
            "python -m src.transformation.silver"
        ),
        cwd=PROJECT_DIRECTORY,
    )

    build_and_validate_gold = BashOperator(
        task_id="build_and_validate_gold",
        bash_command=(
            "python -m src.transformation.gold"
        ),
        cwd=PROJECT_DIRECTORY,
    )

    (
        build_bronze
        >> build_and_validate_silver
        >> build_and_validate_gold
    )