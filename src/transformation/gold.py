"""Build, validate and load analytical tables for the Gold layer."""

from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import get_postgres_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SILVER_ROOT = PROJECT_ROOT / "data" / "silver"
GOLD_ROOT = PROJECT_ROOT / "data" / "gold"
GOLD_SCHEMA = "gold"


def read_silver_table(
    domain: str,
    table_name: str,
    silver_root: Path = SILVER_ROOT,
) -> pd.DataFrame:
    """Read one Silver Parquet table and fail clearly if it is missing."""

    table_path = silver_root / domain / f"{table_name}.parquet"

    if not table_path.exists():
        raise FileNotFoundError(
            f"Silver table not found: {table_path}"
        )

    return pd.read_parquet(table_path)


def build_grade_aggregates(
    grades: pd.DataFrame,
    weight_tolerance: float = 0.01,
) -> pd.DataFrame:
    """Aggregate assessment metrics and normalized grades by enrollment."""

    grades = grades.copy()
    grades["weighted_score"] = (
        grades["score"] * grades["weight"]
    )

    aggregates = (
        grades.groupby("enrollment_id", as_index=False)
        .agg(
            assessment_count=("grade_id", "count"),
            weight_sum=("weight", "sum"),
            weighted_score_sum=("weighted_score", "sum"),
        )
    )

    valid_weight_sum = aggregates["weight_sum"].where(
        aggregates["weight_sum"].ne(0)
    )

    aggregates["normalized_grade"] = (
        aggregates["weighted_score_sum"]
        / valid_weight_sum
    )

    aggregates["has_grades"] = (
        aggregates["assessment_count"] > 0
    )

    aggregates["has_invalid_weight_sum"] = (
        aggregates["weight_sum"]
        .sub(1.0)
        .abs()
        .gt(weight_tolerance)
    )

    return aggregates.drop(
        columns=["weighted_score_sum"]
    )


def build_academic_performance_from_frames(
    enrollments: pd.DataFrame,
    grades: pd.DataFrame,
    courses: pd.DataFrame,
    professors: pd.DataFrame,
    semesters: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Build one analytical row per academic enrollment."""

    grade_aggregates = build_grade_aggregates(grades)

    course_details = courses[
        [
            "course_id",
            "code",
            "name",
            "credits",
            "department",
            "professor_id",
        ]
    ].rename(
        columns={
            "code": "course_code",
            "name": "course_name",
        }
    )

    professor_details = professors[
        [
            "professor_id",
            "first_name",
            "last_name",
        ]
    ].copy()

    professor_details["professor_name"] = (
        professor_details["first_name"].astype("string")
        + " "
        + professor_details["last_name"].astype("string")
    )

    professor_details = professor_details[
        ["professor_id", "professor_name"]
    ]

    semester_details = semesters[
        [
            "semester_id",
            "code",
            "year",
            "half",
        ]
    ].rename(
        columns={
            "code": "semester_code",
            "year": "semester_year",
            "half": "semester_half",
        }
    )

    customer_mapping = (
        customers.loc[
            customers["external_ref"].notna(),
            ["customer_id", "external_ref"],
        ]
        .rename(columns={"external_ref": "student_id"})
        .copy()
    )

    academic_performance = (
        enrollments
        .merge(
            course_details,
            on="course_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            professor_details,
            on="professor_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            semester_details,
            on="semester_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            customer_mapping,
            on="student_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            grade_aggregates,
            on="enrollment_id",
            how="left",
            validate="one_to_one",
        )
    )

    academic_performance["assessment_count"] = (
        academic_performance["assessment_count"]
        .fillna(0)
        .astype("int64")
    )

    academic_performance["has_grades"] = (
        academic_performance["has_grades"]
        .astype("boolean")
        .fillna(False)
        .astype(bool)
    )

    academic_performance["has_invalid_weight_sum"] = (
        academic_performance["has_invalid_weight_sum"]
        .astype("boolean")
        .fillna(False)
        .astype(bool)
    )

    academic_performance = academic_performance.rename(
        columns={"status": "enrollment_status"}
    )

    selected_columns = [
        "enrollment_id",
        "student_id",
        "customer_id",
        "course_id",
        "course_code",
        "course_name",
        "department",
        "credits",
        "professor_id",
        "professor_name",
        "semester_id",
        "semester_code",
        "semester_year",
        "semester_half",
        "enrolled_at",
        "enrollment_status",
        "assessment_count",
        "weight_sum",
        "normalized_grade",
        "has_grades",
        "has_invalid_weight_sum",
    ]

    return academic_performance[selected_columns].copy()


def build_academic_performance(
    silver_root: Path = SILVER_ROOT,
) -> pd.DataFrame:
    """Read Silver inputs and build Gold academic performance."""

    return build_academic_performance_from_frames(
        enrollments=read_silver_table(
            "university", "enrollments", silver_root
        ),
        grades=read_silver_table(
            "university", "grades", silver_root
        ),
        courses=read_silver_table(
            "university", "courses", silver_root
        ),
        professors=read_silver_table(
            "university", "professors", silver_root
        ),
        semesters=read_silver_table(
            "university", "semesters", silver_root
        ),
        customers=read_silver_table(
            "billing", "customers", silver_root
        ),
    )


def validate_academic_performance(
    dataframe: pd.DataFrame,
    expected_rows: int,
) -> dict[str, int | bool]:
    """Validate row grain, relationships and grade calculations."""

    grade_mask = dataframe["has_grades"]

    results: dict[str, int | bool] = {
        "actual_rows": len(dataframe),
        "expected_rows": expected_rows,
        "null_enrollment_ids": int(
            dataframe["enrollment_id"].isna().sum()
        ),
        "duplicated_enrollment_ids": int(
            dataframe["enrollment_id"].duplicated().sum()
        ),
        "missing_customers": int(
            dataframe["customer_id"].isna().sum()
        ),
        "missing_courses": int(
            dataframe["course_name"].isna().sum()
        ),
        "missing_professors": int(
            dataframe["professor_name"].isna().sum()
        ),
        "missing_semesters": int(
            dataframe["semester_code"].isna().sum()
        ),
        "zero_weight_sums": int(
            (
                grade_mask
                & dataframe["weight_sum"].eq(0)
            ).sum()
        ),
        "invalid_normalized_grades": int(
            (
                dataframe["normalized_grade"].notna()
                & ~dataframe["normalized_grade"].between(
                    0,
                    100,
                )
            ).sum()
        ),
    }

    results["is_valid"] = all(
        [
            results["actual_rows"] == results["expected_rows"],
            results["null_enrollment_ids"] == 0,
            results["duplicated_enrollment_ids"] == 0,
            results["missing_customers"] == 0,
            results["missing_courses"] == 0,
            results["missing_professors"] == 0,
            results["missing_semesters"] == 0,
            results["zero_weight_sums"] == 0,
            results["invalid_normalized_grades"] == 0,
        ]
    )

    for rule_name, value in results.items():
        print(f"{rule_name}: {value}")

    if not results["is_valid"]:
        raise ValueError(
            "Gold academic_performance validation failed."
        )

    return results


def ensure_gold_schema(engine: Engine) -> None:
    """Create the Gold schema when it does not already exist."""

    with engine.begin() as connection:
        connection.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {GOLD_SCHEMA}")
        )


def load_gold_table(
    dataframe: pd.DataFrame,
    engine: Engine,
    table_name: str,
    primary_key: str,
) -> None:
    """Replace a Gold table and create its primary key."""

    ensure_gold_schema(engine)

    dataframe.to_sql(
        name=table_name,
        con=engine,
        schema=GOLD_SCHEMA,
        if_exists="replace",
        index=False,
        chunksize=1_000,
        method="multi",
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                ALTER TABLE {GOLD_SCHEMA}.{table_name}
                ADD PRIMARY KEY ({primary_key})
                """
            )
        )


def validate_loaded_table(
    engine: Engine,
    table_name: str,
    primary_key: str,
    expected_rows: int,
) -> dict[str, int | bool]:
    """Validate the row count and grain after PostgreSQL loading."""

    query = text(
        f"""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT {primary_key}) AS distinct_key_count
        FROM {GOLD_SCHEMA}.{table_name}
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query).mappings().one()

    row_count = int(result["row_count"])
    distinct_key_count = int(result["distinct_key_count"])

    validation = {
        "database_rows": row_count,
        "distinct_keys": distinct_key_count,
        "is_valid": (
            row_count == expected_rows
            and distinct_key_count == expected_rows
        ),
    }

    for rule_name, value in validation.items():
        print(f"{rule_name}: {value}")

    if not validation["is_valid"]:
        raise ValueError(
            f"PostgreSQL validation failed for {GOLD_SCHEMA}.{table_name}."
        )

    return validation


def export_gold_parquet(
    dataframe: pd.DataFrame,
    table_name: str,
    gold_root: Path = GOLD_ROOT,
) -> Path:
    """Export one Gold analytical table to Parquet."""

    gold_root.mkdir(parents=True, exist_ok=True)
    output_path = gold_root / f"{table_name}.parquet"

    dataframe.to_parquet(
        output_path,
        index=False,
        engine="pyarrow",
    )

    return output_path


def main() -> None:
    """Build, validate, load and export academic performance."""

    table_name = "academic_performance"
    primary_key = "enrollment_id"

    print("\n" + "=" * 70)
    print("BUILDING GOLD.ACADEMIC_PERFORMANCE")
    print("=" * 70)

    expected_rows = len(
        read_silver_table("university", "enrollments")
    )
    academic_performance = build_academic_performance()

    print("\n" + "=" * 70)
    print("VALIDATING GOLD DATAFRAME")
    print("=" * 70)

    validate_academic_performance(
        academic_performance,
        expected_rows,
    )

    print("\n" + "=" * 70)
    print("LOADING GOLD TABLE INTO POSTGRESQL")
    print("=" * 70)

    engine = get_postgres_engine()
    load_gold_table(
        dataframe=academic_performance,
        engine=engine,
        table_name=table_name,
        primary_key=primary_key,
    )

    print("\n" + "=" * 70)
    print("VALIDATING POSTGRESQL TABLE")
    print("=" * 70)

    validate_loaded_table(
        engine=engine,
        table_name=table_name,
        primary_key=primary_key,
        expected_rows=expected_rows,
    )

    parquet_path = export_gold_parquet(
        academic_performance,
        table_name,
    )

    print("\n" + "=" * 70)
    print("GOLD TABLE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"PostgreSQL table: {GOLD_SCHEMA}.{table_name}")
    print(f"Parquet export: {parquet_path}")


if __name__ == "__main__":
    main()
