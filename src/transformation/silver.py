from pathlib import Path

import pandas as pd

DATE_COLUMNS_BY_FILE: dict[str, list[str]] = {
    "customers": ["created_at"],
    "invoices": ["issued_at", "due_at"],
    "payments": ["paid_at"],
    "subscriptions": ["start_date", "end_date"],
    "accounts": ["created_at"],
    "activities": ["occurred_at"],
    "contacts": ["created_at"],
    "leads": ["created_at"],
    "opportunities": ["close_date", "created_at"],
    "enrollments": ["enrolled_at"],
    "grades": ["graded_at"],
    "professors": ["hired_at"],
    "semesters": ["start_date", "end_date"],
    "students": ["birth_date", "enrolled_at"],
}

PRIMARY_KEYS_BY_FILE: dict[str, list[str]] = {
    "customers": ["customer_id"],
    "invoice_items": ["invoice_item_id"],
    "invoices": ["invoice_id"],
    "payments": ["payment_id"],
    "products": ["product_id"],
    "subscriptions": ["subscription_id"],
    "accounts": ["account_id"],
    "activities": ["activity_id"],
    "contacts": ["contact_id"],
    "leads": ["lead_id"],
    "opportunities": ["opportunity_id"],
    "opportunity_contacts": [
        "opportunity_id",
        "contact_id",
    ],
    "courses": ["course_id"],
    "enrollments": ["enrollment_id"],
    "grades": ["grade_id"],
    "professors": ["professor_id"],
    "semesters": ["semester_id"],
    "students": ["student_id"],
}

FOREIGN_KEY_RELATIONSHIPS: list[
    tuple[str, str, str, str, bool]
] = [
    # Billing
    (
        "billing/invoices",
        "customer_id",
        "billing/customers",
        "customer_id",
        False,
    ),
    (
        "billing/invoice_items",
        "invoice_id",
        "billing/invoices",
        "invoice_id",
        False,
    ),
    (
        "billing/invoice_items",
        "product_id",
        "billing/products",
        "product_id",
        False,
    ),
    (
        "billing/payments",
        "invoice_id",
        "billing/invoices",
        "invoice_id",
        False,
    ),
    (
        "billing/subscriptions",
        "customer_id",
        "billing/customers",
        "customer_id",
        False,
    ),
    (
        "billing/subscriptions",
        "product_id",
        "billing/products",
        "product_id",
        False,
    ),

    # CRM
    (
        "crm/activities",
        "contact_id",
        "crm/contacts",
        "contact_id",
        True,
    ),
    (
        "crm/activities",
        "opportunity_id",
        "crm/opportunities",
        "opportunity_id",
        True,
    ),
    (
        "crm/contacts",
        "account_id",
        "crm/accounts",
        "account_id",
        False,
    ),
    (
        "crm/opportunities",
        "account_id",
        "crm/accounts",
        "account_id",
        False,
    ),
    (
        "crm/opportunity_contacts",
        "opportunity_id",
        "crm/opportunities",
        "opportunity_id",
        False,
    ),
    (
        "crm/opportunity_contacts",
        "contact_id",
        "crm/contacts",
        "contact_id",
        False,
    ),

    # University
    (
        "university/courses",
        "professor_id",
        "university/professors",
        "professor_id",
        False,
    ),
    (
        "university/enrollments",
        "student_id",
        "university/students",
        "student_id",
        False,
    ),
    (
        "university/enrollments",
        "course_id",
        "university/courses",
        "course_id",
        False,
    ),
    (
        "university/enrollments",
        "semester_id",
        "university/semesters",
        "semester_id",
        False,
    ),
    (
        "university/grades",
        "enrollment_id",
        "university/enrollments",
        "enrollment_id",
        False,
    ),
]

DATE_ORDER_RULES: list[
    tuple[str, str, str]
] = [
    (
        "billing/invoices",
        "issued_at",
        "due_at",
    ),
    (
        "billing/subscriptions",
        "start_date",
        "end_date",
    ),
    (
        "crm/opportunities",
        "created_at",
        "close_date",
    ),
    (
        "university/semesters",
        "start_date",
        "end_date",
    ),
]

NUMERIC_RANGE_RULES: list[
    tuple[str, str, float | None, float | None]
] = [
    # Billing
    ("billing/invoice_items", "quantity", 1, None),
    ("billing/invoice_items", "unit_price", 0, None),
    ("billing/invoice_items", "line_total", 0, None),
    ("billing/invoices", "total", 0, None),
    ("billing/payments", "amount", 0, None),
    ("billing/products", "monthly_price", 0, None),

    # CRM
    ("crm/accounts", "annual_revenue", 0, None),
    ("crm/accounts", "employees", 1, None),
    ("crm/leads", "score", 0, 100),
    ("crm/opportunities", "amount", 0, None),

    # University
    ("university/courses", "credits", 1, None),
    ("university/grades", "score", 0, 100),
    ("university/grades", "weight", 0, 1),
]

ALLOWED_VALUES_BY_FILE: dict[
    str,
    dict[str, set[str]],
] = {
    "invoices": {
        "status": {"paid", "pending", "overdue"},
        "currency": {
            "ARS",
            "BRL",
            "CLP",
            "COP",
            "EUR",
            "MXN",
            "PEN",
            "USD",
        },
    },
    "subscriptions": {
        "status": {"active", "cancelled", "paused"},
    },
    "opportunities": {
        "stage": {
            "prospect",
            "qualification",
            "proposal",
            "negotiation",
            "won",
            "lost",
        },
    },
    "enrollments": {
        "status": {
            "active",
            "completed",
            "dropped",
            "failed",
        },
    },
}

def inspect_bronze_files(bronze_root: Path) -> None:
    """Display the structure and data types of every Bronze file."""

    parquet_files = sorted(bronze_root.rglob("*.parquet"))

    print(f"Bronze files found: {len(parquet_files)}")

    for parquet_file in parquet_files:
        dataframe = pd.read_parquet(parquet_file)

        print("\n" + "=" * 70)
        print(f"File: {parquet_file}")
        print(f"Shape: {dataframe.shape}")
        print("\nData types:")
        print(dataframe.dtypes)

        print("\nMissing values:")
        print(dataframe.isna().sum())

        print(f"\nDuplicate rows: {dataframe.duplicated().sum()}")

def inspect_categorical_values(
    parquet_path: Path,
    columns: list[str],
) -> None:
    """Display unique values for selected categorical columns."""

    dataframe = pd.read_parquet(parquet_path)

    print(f"\nFile: {parquet_path}")

    for column in columns:
        print(f"\n{column}:")
        print(
            dataframe[column]
            .value_counts(dropna=False)
            .sort_index()
        )

def convert_date_columns(
    dataframe: pd.DataFrame,
    date_columns: list[str],
) -> pd.DataFrame:
    """Convert selected columns to datetime."""

    dataframe = dataframe.copy()

    for column in date_columns:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
        )

    return dataframe

def transform_silver_dataframe(
    dataframe: pd.DataFrame,
    file_name: str,
) -> pd.DataFrame:
    """Apply Silver transformations according to the source file."""

    date_columns = DATE_COLUMNS_BY_FILE.get(file_name, [])

    silver_dataframe = convert_date_columns(
        dataframe,
        date_columns,
    )

    if file_name == "subscriptions":
        silver_dataframe = clean_invalid_date_order(
            silver_dataframe,
            start_column="start_date",
            end_column="end_date",
            quality_flag_column="end_date_quality_valid",
        )

    if file_name == "opportunities":
        silver_dataframe = clean_invalid_date_order(
            silver_dataframe,
            start_column="created_at",
            end_column="close_date",
            quality_flag_column="close_date_quality_valid",
        )

    return silver_dataframe


def build_silver_path(
    bronze_path: Path,
    bronze_root: Path,
    silver_root: Path,
) -> Path:
    """Build the Silver path from a Bronze Parquet path."""

    relative_path = bronze_path.relative_to(bronze_root)

    return silver_root / relative_path

def process_silver_file(
    bronze_path: Path,
    bronze_root: Path,
    silver_root: Path,
) -> Path:
    """Transform one Bronze file and save it in Silver."""

    dataframe = pd.read_parquet(bronze_path)

    silver_dataframe = transform_silver_dataframe(
        dataframe,
        bronze_path.stem,
    )

    silver_path = build_silver_path(
        bronze_path,
        bronze_root,
        silver_root,
    )

    silver_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    silver_dataframe.to_parquet(
        silver_path,
        index=False,
        engine="pyarrow",
    )

    return silver_path

def run_silver_transformation(
    bronze_root: Path,
    silver_root: Path,
) -> None:
    """Process every Bronze Parquet file into Silver."""

    bronze_files = sorted(
        bronze_root.rglob("*.parquet")
    )

    for bronze_file in bronze_files:
        silver_path = process_silver_file(
            bronze_file,
            bronze_root,
            silver_root,
        )

        print(f"Created: {silver_path}")

def validate_primary_key(
    dataframe: pd.DataFrame,
    primary_keys: list[str],
) -> dict[str, int | bool]:
    """Validate nulls and duplicates in a primary or composite key."""

    null_rows = dataframe[primary_keys].isna().any(axis=1).sum()

    duplicated_rows = dataframe.duplicated(
        subset=primary_keys
    ).sum()

    return {
        "null_rows": int(null_rows),
        "duplicated_rows": int(duplicated_rows),
        "is_valid": bool(
            null_rows == 0
            and duplicated_rows == 0
        ),
    }

def validate_all_primary_keys(
    silver_root: Path,
) -> dict[str, dict[str, int | bool]]:
    """Validate the primary keys of every Silver table."""

    results: dict[str, dict[str, int | bool]] = {}

    silver_files = sorted(
        silver_root.rglob("*.parquet")
    )

    for silver_file in silver_files:
        file_name = silver_file.stem
        primary_keys = PRIMARY_KEYS_BY_FILE.get(file_name)

        if primary_keys is None:
            continue

        dataframe = pd.read_parquet(silver_file)

        validation = validate_primary_key(
            dataframe,
            primary_keys,
        )

        results[file_name] = validation

        status = (
            "VALID"
            if validation["is_valid"]
            else "INVALID"
        )

        print(
            f"{file_name}: {status} "
            f"| null rows: {validation['null_rows']} "
            f"| duplicated rows: "
            f"{validation['duplicated_rows']}"
        )

    return results

def validate_foreign_key(
    child_dataframe: pd.DataFrame,
    child_column: str,
    parent_dataframe: pd.DataFrame,
    parent_column: str,
    allow_nulls: bool = False,
) -> dict[str, int | bool]:
    """Validate that foreign-key values exist in the parent table."""

    foreign_keys = child_dataframe[child_column]

    if allow_nulls:
        foreign_keys = foreign_keys.dropna()

    orphan_rows = ~foreign_keys.isin(
        parent_dataframe[parent_column]
    )

    orphan_count = int(orphan_rows.sum())

    return {
        "orphan_rows": orphan_count,
        "is_valid": orphan_count == 0,
    }

def validate_all_foreign_keys(
    silver_root: Path,
) -> dict[str, dict[str, int | bool]]:
    """Validate every configured foreign-key relationship."""

    results: dict[str, dict[str, int | bool]] = {}
    dataframes: dict[str, pd.DataFrame] = {}

    for (
        child_table,
        child_column,
        parent_table,
        parent_column,
        allow_nulls,
    ) in FOREIGN_KEY_RELATIONSHIPS:

        if child_table not in dataframes:
            dataframes[child_table] = pd.read_parquet(
                silver_root / f"{child_table}.parquet"
            )

        if parent_table not in dataframes:
            dataframes[parent_table] = pd.read_parquet(
                silver_root / f"{parent_table}.parquet"
            )

        validation = validate_foreign_key(
            child_dataframe=dataframes[child_table],
            child_column=child_column,
            parent_dataframe=dataframes[parent_table],
            parent_column=parent_column,
            allow_nulls=allow_nulls,
        )

        relationship_name = (
            f"{child_table}.{child_column} -> "
            f"{parent_table}.{parent_column}"
        )

        results[relationship_name] = validation

        status = (
            "VALID"
            if validation["is_valid"]
            else "INVALID"
        )

        print(
            f"{relationship_name}: {status} "
            f"| orphan rows: {validation['orphan_rows']}"
        )

    return results

def validate_date_order(
    dataframe: pd.DataFrame,
    start_column: str,
    end_column: str,
) -> dict[str, int | bool]:
    """Validate that the end date is not before the start date."""

    invalid_rows = (
        dataframe[end_column] < dataframe[start_column]
    ).sum()

    return {
        "invalid_rows": int(invalid_rows),
        "is_valid": bool(invalid_rows == 0),
    }

def validate_all_date_orders(
    silver_root: Path,
) -> dict[str, dict[str, int | bool]]:
    """Validate all configured chronological rules."""

    results: dict[str, dict[str, int | bool]] = {}

    for table, start_column, end_column in DATE_ORDER_RULES:
        dataframe = pd.read_parquet(
            silver_root / f"{table}.parquet"
        )

        validation = validate_date_order(
            dataframe,
            start_column,
            end_column,
        )

        rule_name = (
            f"{table}.{end_column} >= "
            f"{table}.{start_column}"
        )

        results[rule_name] = validation

        status = (
            "VALID"
            if validation["is_valid"]
            else "INVALID"
        )

        print(
            f"{rule_name}: {status} "
            f"| invalid rows: {validation['invalid_rows']}"
        )

    return results

def inspect_invalid_date_rows(
    dataframe: pd.DataFrame,
    start_column: str,
    end_column: str,
    extra_columns: list[str],
    sample_size: int = 10,
) -> pd.DataFrame:
    """Inspect rows whose end date is before their start date."""

    invalid_mask = (
        dataframe[end_column] < dataframe[start_column]
    )

    columns = [
        *extra_columns,
        start_column,
        end_column,
    ]

    invalid_rows = dataframe.loc[
        invalid_mask,
        columns,
    ].copy()

    invalid_rows["difference_days"] = (
        invalid_rows[end_column]
        - invalid_rows[start_column]
    ).dt.days

    print(f"Invalid rows: {len(invalid_rows)}")
    print(invalid_rows.head(sample_size))

    return invalid_rows

def clean_invalid_date_order(
    dataframe: pd.DataFrame,
    start_column: str,
    end_column: str,
    quality_flag_column: str,
) -> pd.DataFrame:
    """Flag invalid date ranges and nullify invalid end dates."""

    dataframe = dataframe.copy()

    valid_mask = (
        dataframe[start_column].isna()
        | dataframe[end_column].isna()
        | (
            dataframe[end_column].dt.normalize()
            >= dataframe[start_column].dt.normalize()
        )
    )

    dataframe[quality_flag_column] = valid_mask

    dataframe.loc[
        ~valid_mask,
        end_column,
    ] = pd.NaT

    return dataframe

def validate_invoice_line_totals(
    dataframe: pd.DataFrame,
    tolerance: float = 0.01,
) -> dict[str, int | float | bool]:
    """Validate invoice item totals using quantity and unit price."""

    expected_total = (
        dataframe["quantity"]
        * dataframe["unit_price"]
    )

    differences = (
        dataframe["line_total"]
        - expected_total
    ).abs()

    invalid_rows = int(
        (differences > tolerance).sum()
    )

    return {
        "invalid_rows": invalid_rows,
        "maximum_difference": float(differences.max()),
        "is_valid": invalid_rows == 0,
    }

def validate_numeric_range(
    dataframe: pd.DataFrame,
    column: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> dict[str, int | bool]:
    """Validate that numeric values remain within an allowed range."""

    invalid_mask = dataframe[column].isna()

    if minimum is not None:
        invalid_mask |= dataframe[column] < minimum

    if maximum is not None:
        invalid_mask |= dataframe[column] > maximum

    invalid_rows = int(invalid_mask.sum())

    return {
        "invalid_rows": invalid_rows,
        "is_valid": invalid_rows == 0,
    }

def inspect_numeric_columns(
    parquet_path: Path,
    columns: list[str],
) -> None:
    """Display minimum and maximum values of numeric columns."""

    dataframe = pd.read_parquet(parquet_path)

    print(f"\nFile: {parquet_path}")

    for column in columns:
        print(
            f"{column}: "
            f"min={dataframe[column].min()}, "
            f"max={dataframe[column].max()}"
        )

def validate_all_numeric_ranges(
    silver_root: Path,
) -> dict[str, dict[str, int | bool]]:
    """Validate all configured numeric ranges."""

    results: dict[str, dict[str, int | bool]] = {}

    for table, column, minimum, maximum in NUMERIC_RANGE_RULES:
        dataframe = pd.read_parquet(
            silver_root / f"{table}.parquet"
        )

        validation = validate_numeric_range(
            dataframe,
            column=column,
            minimum=minimum,
            maximum=maximum,
        )

        rule_name = f"{table}.{column}"
        results[rule_name] = validation

        status = (
            "VALID"
            if validation["is_valid"]
            else "INVALID"
        )

        print(
            f"{rule_name}: {status} "
            f"| invalid rows: {validation['invalid_rows']}"
        )

    return results

def validate_grade_weights(
    dataframe: pd.DataFrame,
    tolerance: float = 0.01,
) -> dict[str, int | float | bool]:
    """Validate that assessment weights sum to 1 per enrollment."""

    weight_totals = (
        dataframe.groupby("enrollment_id")["weight"]
        .sum()
    )

    differences = (weight_totals - 1.0).abs()

    invalid_enrollments = int(
        (differences > tolerance).sum()
    )

    return {
        "enrollments_checked": int(len(weight_totals)),
        "invalid_enrollments": invalid_enrollments,
        "minimum_weight_sum": float(weight_totals.min()),
        "maximum_weight_sum": float(weight_totals.max()),
        "is_valid": invalid_enrollments == 0,
    }

def validate_allowed_values(
    dataframe: pd.DataFrame,
    column: str,
    allowed_values: set[str],
) -> dict[str, int | bool | list[str]]:
    """Validate that a column only contains allowed categorical values."""

    invalid_mask = (
        dataframe[column].notna()
        & ~dataframe[column].isin(allowed_values)
    )

    invalid_values = sorted(
        dataframe.loc[invalid_mask, column]
        .astype(str)
        .unique()
        .tolist()
    )

    invalid_rows = int(invalid_mask.sum())

    return {
        "invalid_rows": invalid_rows,
        "invalid_values": invalid_values,
        "is_valid": invalid_rows == 0,
    }

def validate_all_allowed_values(
    silver_root: Path,
) -> dict[str, dict[str, int | bool | list[str]]]:
    """Validate all configured categorical values."""

    results: dict[
        str,
        dict[str, int | bool | list[str]],
    ] = {}

    silver_files = sorted(
        silver_root.rglob("*.parquet")
    )

    for silver_file in silver_files:
        file_name = silver_file.stem
        column_rules = ALLOWED_VALUES_BY_FILE.get(file_name)

        if column_rules is None:
            continue

        dataframe = pd.read_parquet(silver_file)

        for column, allowed_values in column_rules.items():
            validation = validate_allowed_values(
                dataframe,
                column,
                allowed_values,
            )

            rule_name = f"{file_name}.{column}"
            results[rule_name] = validation

            status = (
                "VALID"
                if validation["is_valid"]
                else "INVALID"
            )

            print(
                f"{rule_name}: {status} "
                f"| invalid rows: {validation['invalid_rows']} "
                f"| invalid values: {validation['invalid_values']}"
            )

    return results

def validate_date_parsing(
    dataframe: pd.DataFrame,
    date_columns: list[str],
) -> dict[str, dict[str, int | bool]]:
    """Validate that non-null source dates can be parsed."""

    results: dict[str, dict[str, int | bool]] = {}

    for column in date_columns:
        parsed_values = pd.to_datetime(
            dataframe[column],
            errors="coerce",
        )

        invalid_mask = (
            dataframe[column].notna()
            & parsed_values.isna()
        )

        invalid_rows = int(invalid_mask.sum())

        results[column] = {
            "invalid_rows": invalid_rows,
            "is_valid": invalid_rows == 0,
        }

    return results

def validate_all_date_parsing(
    bronze_root: Path,
) -> dict[str, dict[str, int | bool]]:
    """Validate date parsing in every configured Bronze table."""

    results: dict[str, dict[str, int | bool]] = {}

    for bronze_file in sorted(bronze_root.rglob("*.parquet")):
        file_name = bronze_file.stem
        date_columns = DATE_COLUMNS_BY_FILE.get(file_name)

        if date_columns is None:
            continue

        dataframe = pd.read_parquet(bronze_file)

        file_results = validate_date_parsing(
            dataframe,
            date_columns,
        )

        for column, validation in file_results.items():
            rule_name = f"{file_name}.{column}"
            results[rule_name] = validation

            status = (
                "VALID"
                if validation["is_valid"]
                else "INVALID"
            )

            print(
                f"{rule_name}: {status} "
                f"| invalid rows: {validation['invalid_rows']}"
            )

    return results

def validate_all_row_counts(
    bronze_root: Path,
    silver_root: Path,
) -> dict[str, dict[str, int | bool]]:
    """Validate that Silver preserves all Bronze rows."""

    results: dict[str, dict[str, int | bool]] = {}

    for bronze_file in sorted(bronze_root.rglob("*.parquet")):
        relative_path = bronze_file.relative_to(bronze_root)
        silver_file = silver_root / relative_path

        bronze_dataframe = pd.read_parquet(bronze_file)
        silver_dataframe = pd.read_parquet(silver_file)

        bronze_rows = len(bronze_dataframe)
        silver_rows = len(silver_dataframe)

        validation = {
            "bronze_rows": bronze_rows,
            "silver_rows": silver_rows,
            "is_valid": bronze_rows == silver_rows,
        }

        table_name = str(relative_path.with_suffix(""))
        results[table_name] = validation

        status = "VALID" if validation["is_valid"] else "INVALID"

        print(
            f"{table_name}: {status} "
            f"| Bronze rows: {bronze_rows} "
            f"| Silver rows: {silver_rows}"
        )

    return results

def validation_group_is_valid(
    results: dict[str, dict[str, object]],
) -> bool:
    """Return True when every rule in a validation group passes."""

    return all(
        bool(validation["is_valid"])
        for validation in results.values()
    )


def run_silver_validations(
    bronze_root: Path,
    silver_root: Path,
) -> bool:
    """Run all blocking validations for the Silver layer."""

    print("\n" + "=" * 70)
    print("VALIDATING BRONZE DATE PARSING")
    print("=" * 70)

    date_parsing_results = validate_all_date_parsing(
        bronze_root
    )

    print("\n" + "=" * 70)
    print("VALIDATING BRONZE VS SILVER ROW COUNTS")
    print("=" * 70)

    row_count_results = validate_all_row_counts(
        bronze_root,
        silver_root,
    )

    print("\n" + "=" * 70)
    print("VALIDATING PRIMARY KEYS")
    print("=" * 70)

    primary_key_results = validate_all_primary_keys(
        silver_root
    )

    print("\n" + "=" * 70)
    print("VALIDATING FOREIGN KEYS")
    print("=" * 70)

    foreign_key_results = validate_all_foreign_keys(
        silver_root
    )

    print("\n" + "=" * 70)
    print("VALIDATING DATE ORDER")
    print("=" * 70)

    date_order_results = validate_all_date_orders(
        silver_root
    )

    print("\n" + "=" * 70)
    print("VALIDATING NUMERIC RANGES")
    print("=" * 70)

    numeric_range_results = validate_all_numeric_ranges(
        silver_root
    )

    print("\n" + "=" * 70)
    print("VALIDATING CATEGORICAL VALUES")
    print("=" * 70)

    allowed_value_results = validate_all_allowed_values(
        silver_root
    )

    print("\n" + "=" * 70)
    print("VALIDATING INVOICE LINE TOTALS")
    print("=" * 70)

    invoice_items = pd.read_parquet(
        silver_root / "billing/invoice_items.parquet"
    )

    invoice_line_result = validate_invoice_line_totals(
        invoice_items
    )

    invoice_line_status = (
        "VALID"
        if invoice_line_result["is_valid"]
        else "INVALID"
    )

    print(
        f"billing/invoice_items.line_total: "
        f"{invoice_line_status} "
        f"| invalid rows: "
        f"{invoice_line_result['invalid_rows']} "
        f"| maximum difference: "
        f"{invoice_line_result['maximum_difference']}"
    )

    validation_groups = [
        date_parsing_results,
        row_count_results,
        primary_key_results,
        foreign_key_results,
        date_order_results,
        numeric_range_results,
        allowed_value_results,
    ]

    blocking_validations_passed = (
        all(
            validation_group_is_valid(group)
            for group in validation_groups
        )
        and bool(invoice_line_result["is_valid"])
    )

    return blocking_validations_passed

def report_silver_quality_warnings(
    silver_root: Path,
) -> None:
    """Report source-data issues that should not stop the pipeline."""

    print("\n" + "=" * 70)
    print("NON-BLOCKING DATA QUALITY WARNINGS")
    print("=" * 70)

    grades = pd.read_parquet(
        silver_root / "university/grades.parquet"
    )

    grade_weight_result = validate_grade_weights(grades)

    status = (
        "VALID"
        if grade_weight_result["is_valid"]
        else "WARNING"
    )

    print(
        f"university/grades.weight_sum: {status} "
        f"| enrollments checked: "
        f"{grade_weight_result['enrollments_checked']} "
        f"| invalid enrollments: "
        f"{grade_weight_result['invalid_enrollments']} "
        f"| minimum sum: "
        f"{grade_weight_result['minimum_weight_sum']} "
        f"| maximum sum: "
        f"{grade_weight_result['maximum_weight_sum']}"
    )
def main() -> None:
    """Run the complete Silver transformation and validation process."""

    bronze_root = Path("data/bronze")
    silver_root = Path("data/silver")

    print("\n" + "=" * 70)
    print("STARTING SILVER TRANSFORMATION")
    print("=" * 70)

    run_silver_transformation(
        bronze_root=bronze_root,
        silver_root=silver_root,
    )

    validations_passed = run_silver_validations(
        bronze_root=bronze_root,
        silver_root=silver_root,
    )

    report_silver_quality_warnings(silver_root)

    print("\n" + "=" * 70)

    if not validations_passed:
        print("SILVER PIPELINE FAILED")
        print("=" * 70)

        raise RuntimeError(
            "One or more blocking Silver validations failed."
        )

    print("SILVER PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
