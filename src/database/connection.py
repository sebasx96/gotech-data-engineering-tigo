"""PostgreSQL connection utilities for the data pipeline."""

from functools import lru_cache
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def get_required_environment_variable(name: str) -> str:
    """Return a required environment variable or raise a clear error."""

    value = getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"Required environment variable '{name}' is not configured."
        )

    return value


@lru_cache(maxsize=1)
def get_postgres_engine() -> Engine:
    """Create and cache the SQLAlchemy PostgreSQL engine."""

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=get_required_environment_variable("POSTGRES_USER"),
        password=get_required_environment_variable("POSTGRES_PASSWORD"),
        host=getenv("POSTGRES_HOST", "localhost"),
        port=int(getenv("POSTGRES_PORT", "5432")),
        database=get_required_environment_variable("POSTGRES_DB"),
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def test_postgres_connection() -> dict[str, str]:
    """Connect to PostgreSQL and return basic connection information."""

    query = text(
        """
        SELECT
            current_database() AS database_name,
            current_user AS database_user,
            current_schema() AS active_schema
        """
    )

    try:
        with get_postgres_engine().connect() as connection:
            result = connection.execute(query).mappings().one()

    except SQLAlchemyError as error:
        raise RuntimeError(
            "Python could not connect to PostgreSQL."
        ) from error

    return {
        "database_name": str(result["database_name"]),
        "database_user": str(result["database_user"]),
        "active_schema": str(result["active_schema"]),
    }


def main() -> None:
    """Run a PostgreSQL connection test."""

    connection_information = test_postgres_connection()

    print("PostgreSQL connection successful")
    print(
        f"Database: {connection_information['database_name']}"
    )
    print(
        f"User: {connection_information['database_user']}"
    )
    print(
        f"Active schema: "
        f"{connection_information['active_schema']}"
    )


if __name__ == "__main__":
    main()