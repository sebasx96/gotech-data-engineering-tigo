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
MONETARY_TOLERANCE = 0.01


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


def build_invoice_item_aggregates(
    invoice_items: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate invoice-line metrics by invoice."""

    aggregates = (
        invoice_items.groupby("invoice_id", as_index=False)
        .agg(
            invoice_item_count=("invoice_item_id", "count"),
            invoice_item_total=("line_total", "sum"),
        )
    )

    aggregates["invoice_item_total"] = (
        aggregates["invoice_item_total"].round(2)
    )

    return aggregates


def build_payment_aggregates(
    payments: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate payment metrics by invoice."""

    aggregates = (
        payments.groupby("invoice_id", as_index=False)
        .agg(
            payment_count=("payment_id", "count"),
            paid_amount=("amount", "sum"),
            first_payment_at=("paid_at", "min"),
            last_payment_at=("paid_at", "max"),
        )
    )

    aggregates["paid_amount"] = (
        aggregates["paid_amount"].round(2)
    )

    return aggregates


def build_invoice_financial_from_frames(
    invoices: pd.DataFrame,
    invoice_items: pd.DataFrame,
    payments: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Build one analytical row per invoice."""

    item_aggregates = build_invoice_item_aggregates(
        invoice_items
    )
    payment_aggregates = build_payment_aggregates(
        payments
    )

    customer_details = customers[
        [
            "customer_id",
            "external_ref",
            "segment",
            "country",
        ]
    ].rename(
        columns={
            "external_ref": "student_id",
            "segment": "customer_segment",
            "country": "customer_country",
        }
    )

    invoice_financial = (
        invoices
        .merge(
            customer_details,
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            item_aggregates,
            on="invoice_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            payment_aggregates,
            on="invoice_id",
            how="left",
            validate="one_to_one",
        )
        .rename(
            columns={
                "status": "invoice_status",
                "total": "invoice_total",
            }
        )
    )

    invoice_financial["invoice_item_count"] = (
        invoice_financial["invoice_item_count"]
        .fillna(0)
        .astype("int64")
    )
    invoice_financial["invoice_item_total"] = (
        invoice_financial["invoice_item_total"]
        .fillna(0.0)
        .round(2)
    )
    invoice_financial["payment_count"] = (
        invoice_financial["payment_count"]
        .fillna(0)
        .astype("int64")
    )
    invoice_financial["paid_amount"] = (
        invoice_financial["paid_amount"]
        .fillna(0.0)
        .round(2)
    )

    invoice_financial["invoice_total"] = (
        invoice_financial["invoice_total"].round(2)
    )

    invoice_financial["invoice_item_difference"] = (
        invoice_financial["invoice_item_total"]
        - invoice_financial["invoice_total"]
    ).round(2)

    invoice_financial["balance_amount"] = (
        invoice_financial["invoice_total"]
        - invoice_financial["paid_amount"]
    ).round(2)

    invoice_financial["outstanding_amount"] = (
        invoice_financial["balance_amount"]
        .clip(lower=0)
        .round(2)
    )

    invoice_financial["overpayment_amount"] = (
        -invoice_financial["balance_amount"]
    ).clip(lower=0).round(2)

    invoice_financial["has_invoice_items"] = (
        invoice_financial["invoice_item_count"] > 0
    )
    invoice_financial["has_payments"] = (
        invoice_financial["payment_count"] > 0
    )
    invoice_financial["is_student_customer"] = (
        invoice_financial["student_id"].notna()
    )

    invoice_financial["invoice_items_match_header"] = (
        invoice_financial["has_invoice_items"]
        & invoice_financial["invoice_item_difference"]
        .abs()
        .le(MONETARY_TOLERANCE)
    )

    invoice_financial["is_balanced"] = (
        invoice_financial["balance_amount"]
        .abs()
        .le(MONETARY_TOLERANCE)
    )
    invoice_financial["is_outstanding"] = (
        invoice_financial["outstanding_amount"]
        .gt(MONETARY_TOLERANCE)
    )
    invoice_financial["is_overpaid"] = (
        invoice_financial["overpayment_amount"]
        .gt(MONETARY_TOLERANCE)
    )

    paid_status = invoice_financial["invoice_status"].eq(
        "paid"
    )
    open_status = invoice_financial["invoice_status"].isin(
        ["pending", "overdue"]
    )

    invoice_financial["payment_status_matches_balance"] = (
        (paid_status & ~invoice_financial["is_outstanding"])
        | (open_status & invoice_financial["is_outstanding"])
    )

    selected_columns = [
        "invoice_id",
        "customer_id",
        "student_id",
        "customer_segment",
        "customer_country",
        "issued_at",
        "due_at",
        "invoice_status",
        "currency",
        "invoice_total",
        "invoice_item_count",
        "invoice_item_total",
        "invoice_item_difference",
        "payment_count",
        "paid_amount",
        "first_payment_at",
        "last_payment_at",
        "balance_amount",
        "outstanding_amount",
        "overpayment_amount",
        "has_invoice_items",
        "has_payments",
        "is_student_customer",
        "invoice_items_match_header",
        "is_balanced",
        "is_outstanding",
        "is_overpaid",
        "payment_status_matches_balance",
    ]

    return invoice_financial[selected_columns].copy()


def build_invoice_financial(
    silver_root: Path = SILVER_ROOT,
) -> pd.DataFrame:
    """Read Silver inputs and build Gold invoice financial."""

    return build_invoice_financial_from_frames(
        invoices=read_silver_table(
            "billing", "invoices", silver_root
        ),
        invoice_items=read_silver_table(
            "billing", "invoice_items", silver_root
        ),
        payments=read_silver_table(
            "billing", "payments", silver_root
        ),
        customers=read_silver_table(
            "billing", "customers", silver_root
        ),
    )


def validate_invoice_financial(
    dataframe: pd.DataFrame,
    expected_rows: int,
) -> dict[str, int | bool]:
    """Validate invoice grain, relationships and financial calculations."""

    expected_balance = (
        dataframe["invoice_total"]
        - dataframe["paid_amount"]
    ).round(2)

    expected_split_balance = (
        dataframe["outstanding_amount"]
        - dataframe["overpayment_amount"]
    ).round(2)

    results: dict[str, int | bool] = {
        "actual_rows": len(dataframe),
        "expected_rows": expected_rows,
        "null_invoice_ids": int(
            dataframe["invoice_id"].isna().sum()
        ),
        "duplicated_invoice_ids": int(
            dataframe["invoice_id"].duplicated().sum()
        ),
        "missing_customers": int(
            dataframe["customer_segment"].isna().sum()
        ),
        "missing_currencies": int(
            dataframe["currency"].isna().sum()
        ),
        "negative_invoice_totals": int(
            dataframe["invoice_total"].lt(0).sum()
        ),
        "negative_invoice_item_totals": int(
            dataframe["invoice_item_total"].lt(0).sum()
        ),
        "negative_paid_amounts": int(
            dataframe["paid_amount"].lt(0).sum()
        ),
        "invalid_balance_calculations": int(
            dataframe["balance_amount"]
            .sub(expected_balance)
            .abs()
            .gt(MONETARY_TOLERANCE)
            .sum()
        ),
        "invalid_balance_splits": int(
            expected_split_balance
            .sub(dataframe["balance_amount"])
            .abs()
            .gt(MONETARY_TOLERANCE)
            .sum()
        ),
        "contradictory_balance_flags": int(
            (
                dataframe["is_outstanding"]
                & dataframe["is_overpaid"]
            ).sum()
        ),
        "invalid_item_flags": int(
            (
                dataframe["has_invoice_items"]
                != dataframe["invoice_item_count"].gt(0)
            ).sum()
        ),
        "invalid_payment_flags": int(
            (
                dataframe["has_payments"]
                != dataframe["payment_count"].gt(0)
            ).sum()
        ),
        "student_invoices": int(
            dataframe["is_student_customer"].sum()
        ),
        "invoices_without_items": int(
            (~dataframe["has_invoice_items"]).sum()
        ),
        "invoices_without_payments": int(
            (~dataframe["has_payments"]).sum()
        ),
        "invoice_item_mismatches": int(
            (
                dataframe["has_invoice_items"]
                & ~dataframe["invoice_items_match_header"]
            ).sum()
        ),
        "balanced_invoices": int(
            dataframe["is_balanced"].sum()
        ),
        "outstanding_invoices": int(
            dataframe["is_outstanding"].sum()
        ),
        "overpaid_invoices": int(
            dataframe["is_overpaid"].sum()
        ),
        "status_balance_mismatches": int(
            (~dataframe["payment_status_matches_balance"]).sum()
        ),
    }

    results["is_valid"] = all(
        [
            results["actual_rows"] == results["expected_rows"],
            results["null_invoice_ids"] == 0,
            results["duplicated_invoice_ids"] == 0,
            results["missing_customers"] == 0,
            results["missing_currencies"] == 0,
            results["negative_invoice_totals"] == 0,
            results["negative_invoice_item_totals"] == 0,
            results["negative_paid_amounts"] == 0,
            results["invalid_balance_calculations"] == 0,
            results["invalid_balance_splits"] == 0,
            results["contradictory_balance_flags"] == 0,
            results["invalid_item_flags"] == 0,
            results["invalid_payment_flags"] == 0,
        ]
    )

    for rule_name, value in results.items():
        print(f"{rule_name}: {value}")

    if not results["is_valid"]:
        raise ValueError(
            "Gold invoice_financial validation failed."
        )

    return results



def build_product_sales_from_frames(
    invoice_items: pd.DataFrame,
    invoices: pd.DataFrame,
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Build one analytical row per invoice item."""

    invoice_details = invoices[
        [
            "invoice_id",
            "customer_id",
            "issued_at",
            "status",
            "currency",
        ]
    ].rename(
        columns={"status": "invoice_status"}
    )

    product_details = products[
        [
            "product_id",
            "sku",
            "name",
            "category",
            "monthly_price",
            "active",
        ]
    ].rename(
        columns={
            "name": "product_name",
            "category": "product_category",
            "monthly_price": "product_monthly_price",
            "active": "product_active",
        }
    )

    customer_details = customers[
        [
            "customer_id",
            "external_ref",
            "segment",
            "country",
        ]
    ].rename(
        columns={
            "external_ref": "student_id",
            "segment": "customer_segment",
            "country": "customer_country",
        }
    )

    product_sales = (
        invoice_items
        .merge(
            invoice_details,
            on="invoice_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            product_details,
            on="product_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            customer_details,
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
    )

    product_sales["is_student_customer"] = (
        product_sales["student_id"].notna()
    )

    monetary_columns = [
        "unit_price",
        "line_total",
        "product_monthly_price",
    ]

    product_sales[monetary_columns] = (
        product_sales[monetary_columns].round(2)
    )

    selected_columns = [
        "invoice_item_id",
        "invoice_id",
        "customer_id",
        "student_id",
        "is_student_customer",
        "customer_segment",
        "customer_country",
        "product_id",
        "sku",
        "product_name",
        "product_category",
        "product_monthly_price",
        "product_active",
        "issued_at",
        "invoice_status",
        "currency",
        "quantity",
        "unit_price",
        "line_total",
    ]

    return product_sales[selected_columns].copy()


def build_product_sales(
    silver_root: Path = SILVER_ROOT,
) -> pd.DataFrame:
    """Read Silver inputs and build Gold product sales."""

    return build_product_sales_from_frames(
        invoice_items=read_silver_table(
            "billing", "invoice_items", silver_root
        ),
        invoices=read_silver_table(
            "billing", "invoices", silver_root
        ),
        products=read_silver_table(
            "billing", "products", silver_root
        ),
        customers=read_silver_table(
            "billing", "customers", silver_root
        ),
    )


def validate_product_sales(
    dataframe: pd.DataFrame,
    expected_rows: int,
) -> dict[str, int | bool]:
    """Validate product-sales grain, joins and line calculations."""

    expected_line_total = (
        dataframe["quantity"]
        * dataframe["unit_price"]
    ).round(2)

    results: dict[str, int | bool] = {
        "actual_rows": len(dataframe),
        "expected_rows": expected_rows,
        "null_invoice_item_ids": int(
            dataframe["invoice_item_id"].isna().sum()
        ),
        "duplicated_invoice_item_ids": int(
            dataframe["invoice_item_id"].duplicated().sum()
        ),
        "missing_invoices": int(
            dataframe["issued_at"].isna().sum()
        ),
        "missing_customers": int(
            dataframe["customer_segment"].isna().sum()
        ),
        "missing_products": int(
            dataframe["sku"].isna().sum()
        ),
        "missing_currencies": int(
            dataframe["currency"].isna().sum()
        ),
        "non_positive_quantities": int(
            dataframe["quantity"].le(0).sum()
        ),
        "negative_unit_prices": int(
            dataframe["unit_price"].lt(0).sum()
        ),
        "negative_line_totals": int(
            dataframe["line_total"].lt(0).sum()
        ),
        "invalid_line_calculations": int(
            dataframe["line_total"]
            .sub(expected_line_total)
            .abs()
            .gt(MONETARY_TOLERANCE)
            .sum()
        ),
        "student_sales_lines": int(
            dataframe["is_student_customer"].sum()
        ),
        "non_student_sales_lines": int(
            (~dataframe["is_student_customer"]).sum()
        ),
        "currency_count": int(
            dataframe["currency"].nunique()
        ),
        "product_category_count": int(
            dataframe["product_category"].nunique()
        ),
    }

    results["is_valid"] = all(
        [
            results["actual_rows"] == results["expected_rows"],
            results["null_invoice_item_ids"] == 0,
            results["duplicated_invoice_item_ids"] == 0,
            results["missing_invoices"] == 0,
            results["missing_customers"] == 0,
            results["missing_products"] == 0,
            results["missing_currencies"] == 0,
            results["non_positive_quantities"] == 0,
            results["negative_unit_prices"] == 0,
            results["negative_line_totals"] == 0,
            results["invalid_line_calculations"] == 0,
        ]
    )

    for rule_name, value in results.items():
        print(f"{rule_name}: {value}")

    if not results["is_valid"]:
        raise ValueError(
            "Gold product_sales validation failed."
        )

    return results


def build_subscription_portfolio_from_frames(
    subscriptions: pd.DataFrame,
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Build one analytical row per subscription."""

    product_details = products[
        [
            "product_id",
            "sku",
            "name",
            "category",
            "monthly_price",
            "active",
        ]
    ].rename(
        columns={
            "name": "product_name",
            "category": "product_category",
            "monthly_price": "product_monthly_price",
            "active": "product_active",
        }
    )

    customer_details = customers[
        [
            "customer_id",
            "external_ref",
            "segment",
            "country",
            "created_at",
        ]
    ].rename(
        columns={
            "external_ref": "student_id",
            "segment": "customer_segment",
            "country": "customer_country",
            "created_at": "customer_created_at",
        }
    )

    subscription_portfolio = (
        subscriptions
        .merge(
            product_details,
            on="product_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            customer_details,
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
        .rename(
            columns={"status": "subscription_status"}
        )
    )

    subscription_portfolio["duration_days"] = (
        subscription_portfolio["end_date"]
        - subscription_portfolio["start_date"]
    ).dt.days.astype("Int64")

    subscription_portfolio["is_active"] = (
        subscription_portfolio["subscription_status"]
        .eq("active")
    )
    subscription_portfolio["is_student_customer"] = (
        subscription_portfolio["student_id"].notna()
    )
    subscription_portfolio["invalid_end_date_flag"] = (
        ~subscription_portfolio["end_date_quality_valid"]
    )

    subscription_portfolio["product_monthly_price"] = (
        subscription_portfolio["product_monthly_price"]
        .round(2)
    )

    selected_columns = [
        "subscription_id",
        "customer_id",
        "student_id",
        "is_student_customer",
        "customer_segment",
        "customer_country",
        "customer_created_at",
        "product_id",
        "sku",
        "product_name",
        "product_category",
        "product_monthly_price",
        "product_active",
        "subscription_status",
        "start_date",
        "end_date",
        "duration_days",
        "is_active",
        "invalid_end_date_flag",
    ]

    return subscription_portfolio[selected_columns].copy()


def build_subscription_portfolio(
    silver_root: Path = SILVER_ROOT,
) -> pd.DataFrame:
    """Read Silver inputs and build Gold subscription portfolio."""

    return build_subscription_portfolio_from_frames(
        subscriptions=read_silver_table(
            "billing", "subscriptions", silver_root
        ),
        products=read_silver_table(
            "billing", "products", silver_root
        ),
        customers=read_silver_table(
            "billing", "customers", silver_root
        ),
    )


def validate_subscription_portfolio(
    dataframe: pd.DataFrame,
    expected_rows: int,
) -> dict[str, int | float | bool]:
    """Validate subscription grain, joins, dates and quality flags."""

    expected_active_flag = (
        dataframe["subscription_status"].eq("active")
    )
    expected_student_flag = (
        dataframe["student_id"].notna()
    )

    valid_date_mask = (
        ~dataframe["invalid_end_date_flag"]
        & dataframe["end_date"].notna()
    )

    duration_values = dataframe["duration_days"].dropna()

    results: dict[str, int | float | bool] = {
        "actual_rows": len(dataframe),
        "expected_rows": expected_rows,
        "null_subscription_ids": int(
            dataframe["subscription_id"].isna().sum()
        ),
        "duplicated_subscription_ids": int(
            dataframe["subscription_id"].duplicated().sum()
        ),
        "missing_customers": int(
            dataframe["customer_segment"].isna().sum()
        ),
        "missing_products": int(
            dataframe["sku"].isna().sum()
        ),
        "missing_statuses": int(
            dataframe["subscription_status"].isna().sum()
        ),
        "missing_start_dates": int(
            dataframe["start_date"].isna().sum()
        ),
        "negative_monthly_prices": int(
            dataframe["product_monthly_price"].lt(0).sum()
        ),
        "negative_durations": int(
            dataframe["duration_days"].lt(0).sum()
        ),
        "invalid_dates_still_present": int(
            (
                dataframe["invalid_end_date_flag"]
                & dataframe["end_date"].notna()
            ).sum()
        ),
        "invalid_valid_date_orders": int(
            (
                valid_date_mask
                & dataframe["end_date"].lt(
                    dataframe["start_date"]
                )
            ).sum()
        ),
        "invalid_active_flags": int(
            (
                dataframe["is_active"]
                != expected_active_flag
            ).sum()
        ),
        "invalid_student_flags": int(
            (
                dataframe["is_student_customer"]
                != expected_student_flag
            ).sum()
        ),
        "active_subscriptions": int(
            dataframe["is_active"].sum()
        ),
        "paused_subscriptions": int(
            dataframe["subscription_status"].eq("paused").sum()
        ),
        "cancelled_subscriptions": int(
            dataframe["subscription_status"].eq("cancelled").sum()
        ),
        "student_subscriptions": int(
            dataframe["is_student_customer"].sum()
        ),
        "non_student_subscriptions": int(
            (~dataframe["is_student_customer"]).sum()
        ),
        "invalid_end_dates": int(
            dataframe["invalid_end_date_flag"].sum()
        ),
        "subscriptions_without_end_date": int(
            dataframe["end_date"].isna().sum()
        ),
        "inactive_product_subscriptions": int(
            (~dataframe["product_active"]).sum()
        ),
        "product_category_count": int(
            dataframe["product_category"].nunique()
        ),
        "average_duration_days": round(
            float(duration_values.mean()),
            2,
        ),
    }

    results["is_valid"] = all(
        [
            results["actual_rows"] == results["expected_rows"],
            results["null_subscription_ids"] == 0,
            results["duplicated_subscription_ids"] == 0,
            results["missing_customers"] == 0,
            results["missing_products"] == 0,
            results["missing_statuses"] == 0,
            results["missing_start_dates"] == 0,
            results["negative_monthly_prices"] == 0,
            results["negative_durations"] == 0,
            results["invalid_dates_still_present"] == 0,
            results["invalid_valid_date_orders"] == 0,
            results["invalid_active_flags"] == 0,
            results["invalid_student_flags"] == 0,
        ]
    )

    for rule_name, value in results.items():
        print(f"{rule_name}: {value}")

    if not results["is_valid"]:
        raise ValueError(
            "Gold subscription_portfolio validation failed."
        )

    return results


def build_opportunity_activity_aggregates(
    activities: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate activity metrics by opportunity."""

    opportunity_activities = activities.loc[
        activities["opportunity_id"].notna()
    ].copy()

    aggregates = (
        opportunity_activities
        .groupby("opportunity_id", as_index=False)
        .agg(
            activity_count=("activity_id", "count"),
            first_activity_at=("occurred_at", "min"),
            last_activity_at=("occurred_at", "max"),
        )
    )

    activity_type_counts = (
        opportunity_activities
        .pivot_table(
            index="opportunity_id",
            columns="type",
            values="activity_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(columns=None)
    )

    activity_columns = {
        "call": "call_activity_count",
        "demo": "demo_activity_count",
        "email": "email_activity_count",
        "meeting": "meeting_activity_count",
        "note": "note_activity_count",
    }

    for source_column in activity_columns:
        if source_column not in activity_type_counts.columns:
            activity_type_counts[source_column] = 0

    activity_type_counts = activity_type_counts.rename(
        columns=activity_columns
    )

    return aggregates.merge(
        activity_type_counts[
            [
                "opportunity_id",
                "call_activity_count",
                "demo_activity_count",
                "email_activity_count",
                "meeting_activity_count",
                "note_activity_count",
            ]
        ],
        on="opportunity_id",
        how="left",
        validate="one_to_one",
    )


def build_opportunity_contact_aggregates(
    opportunity_contacts: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate distinct CRM contacts by opportunity."""

    return (
        opportunity_contacts
        .groupby("opportunity_id", as_index=False)
        .agg(
            contact_count=("contact_id", "nunique"),
        )
    )


def build_crm_opportunity_from_frames(
    opportunities: pd.DataFrame,
    accounts: pd.DataFrame,
    activities: pd.DataFrame,
    opportunity_contacts: pd.DataFrame,
) -> pd.DataFrame:
    """Build one analytical row per CRM opportunity."""

    account_details = accounts[
        [
            "account_id",
            "name",
            "industry",
            "country",
            "annual_revenue",
            "employees",
        ]
    ].rename(
        columns={
            "name": "account_name",
            "country": "account_country",
            "annual_revenue": "account_annual_revenue",
            "employees": "account_employees",
        }
    )

    activity_aggregates = build_opportunity_activity_aggregates(
        activities
    )
    contact_aggregates = build_opportunity_contact_aggregates(
        opportunity_contacts
    )

    crm_opportunity = (
        opportunities
        .rename(columns={"name": "opportunity_name"})
        .merge(
            account_details,
            on="account_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            activity_aggregates,
            on="opportunity_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            contact_aggregates,
            on="opportunity_id",
            how="left",
            validate="one_to_one",
        )
    )

    count_columns = [
        "activity_count",
        "call_activity_count",
        "demo_activity_count",
        "email_activity_count",
        "meeting_activity_count",
        "note_activity_count",
        "contact_count",
    ]

    crm_opportunity[count_columns] = (
        crm_opportunity[count_columns]
        .fillna(0)
        .astype("int64")
    )

    crm_opportunity["amount"] = (
        crm_opportunity["amount"].round(2)
    )
    crm_opportunity["account_annual_revenue"] = (
        crm_opportunity["account_annual_revenue"].round(2)
    )

    crm_opportunity["has_activities"] = (
        crm_opportunity["activity_count"].gt(0)
    )
    crm_opportunity["has_contacts"] = (
        crm_opportunity["contact_count"].gt(0)
    )
    crm_opportunity["is_won"] = (
        crm_opportunity["stage"].eq("won")
    )
    crm_opportunity["is_lost"] = (
        crm_opportunity["stage"].eq("lost")
    )
    crm_opportunity["is_closed"] = (
        crm_opportunity["stage"].isin(["won", "lost"])
    )
    crm_opportunity["is_open"] = (
        ~crm_opportunity["is_closed"]
    )
    crm_opportunity["invalid_close_date_flag"] = (
        ~crm_opportunity["close_date_quality_valid"]
    )

    selected_columns = [
        "opportunity_id",
        "opportunity_name",
        "account_id",
        "account_name",
        "industry",
        "account_country",
        "account_annual_revenue",
        "account_employees",
        "stage",
        "amount",
        "created_at",
        "close_date",
        "activity_count",
        "call_activity_count",
        "demo_activity_count",
        "email_activity_count",
        "meeting_activity_count",
        "note_activity_count",
        "first_activity_at",
        "last_activity_at",
        "has_activities",
        "contact_count",
        "has_contacts",
        "is_open",
        "is_closed",
        "is_won",
        "is_lost",
        "invalid_close_date_flag",
    ]

    return crm_opportunity[selected_columns].copy()


def build_crm_opportunity(
    silver_root: Path = SILVER_ROOT,
) -> pd.DataFrame:
    """Read Silver inputs and build Gold CRM opportunities."""

    return build_crm_opportunity_from_frames(
        opportunities=read_silver_table(
            "crm", "opportunities", silver_root
        ),
        accounts=read_silver_table(
            "crm", "accounts", silver_root
        ),
        activities=read_silver_table(
            "crm", "activities", silver_root
        ),
        opportunity_contacts=read_silver_table(
            "crm", "opportunity_contacts", silver_root
        ),
    )


def validate_crm_opportunity(
    dataframe: pd.DataFrame,
    expected_rows: int,
) -> dict[str, int | bool | float]:
    """Validate CRM-opportunity grain, joins and analytical flags."""

    expected_activity_flag = dataframe["activity_count"].gt(0)
    expected_contact_flag = dataframe["contact_count"].gt(0)
    expected_won_flag = dataframe["stage"].eq("won")
    expected_lost_flag = dataframe["stage"].eq("lost")
    expected_closed_flag = dataframe["stage"].isin(
        ["won", "lost"]
    )
    expected_open_flag = ~expected_closed_flag

    activity_type_total = dataframe[
        [
            "call_activity_count",
            "demo_activity_count",
            "email_activity_count",
            "meeting_activity_count",
            "note_activity_count",
        ]
    ].sum(axis=1)

    results: dict[str, int | bool | float] = {
        "actual_rows": len(dataframe),
        "expected_rows": expected_rows,
        "null_opportunity_ids": int(
            dataframe["opportunity_id"].isna().sum()
        ),
        "duplicated_opportunity_ids": int(
            dataframe["opportunity_id"].duplicated().sum()
        ),
        "missing_accounts": int(
            dataframe["account_name"].isna().sum()
        ),
        "missing_stages": int(
            dataframe["stage"].isna().sum()
        ),
        "negative_amounts": int(
            dataframe["amount"].lt(0).sum()
        ),
        "negative_activity_counts": int(
            dataframe["activity_count"].lt(0).sum()
        ),
        "negative_contact_counts": int(
            dataframe["contact_count"].lt(0).sum()
        ),
        "invalid_activity_type_totals": int(
            activity_type_total
            .ne(dataframe["activity_count"])
            .sum()
        ),
        "invalid_activity_flags": int(
            dataframe["has_activities"]
            .ne(expected_activity_flag)
            .sum()
        ),
        "invalid_contact_flags": int(
            dataframe["has_contacts"]
            .ne(expected_contact_flag)
            .sum()
        ),
        "invalid_won_flags": int(
            dataframe["is_won"]
            .ne(expected_won_flag)
            .sum()
        ),
        "invalid_lost_flags": int(
            dataframe["is_lost"]
            .ne(expected_lost_flag)
            .sum()
        ),
        "invalid_closed_flags": int(
            dataframe["is_closed"]
            .ne(expected_closed_flag)
            .sum()
        ),
        "invalid_open_flags": int(
            dataframe["is_open"]
            .ne(expected_open_flag)
            .sum()
        ),
        "contradictory_open_closed_flags": int(
            (
                dataframe["is_open"]
                & dataframe["is_closed"]
            ).sum()
        ),
        "invalid_dates_still_present": int(
            (
                dataframe["invalid_close_date_flag"]
                & dataframe["close_date"].notna()
            ).sum()
        ),
        "invalid_valid_date_orders": int(
            (
                ~dataframe["invalid_close_date_flag"]
                & dataframe["close_date"].notna()
                & dataframe["close_date"].lt(
                    dataframe["created_at"]
                )
            ).sum()
        ),
        "open_opportunities": int(
            dataframe["is_open"].sum()
        ),
        "closed_opportunities": int(
            dataframe["is_closed"].sum()
        ),
        "won_opportunities": int(
            dataframe["is_won"].sum()
        ),
        "lost_opportunities": int(
            dataframe["is_lost"].sum()
        ),
        "opportunities_without_activities": int(
            (~dataframe["has_activities"]).sum()
        ),
        "opportunities_without_contacts": int(
            (~dataframe["has_contacts"]).sum()
        ),
        "invalid_close_dates": int(
            dataframe["invalid_close_date_flag"].sum()
        ),
        "average_activity_count": round(
            float(dataframe["activity_count"].mean()),
            2,
        ),
        "average_contact_count": round(
            float(dataframe["contact_count"].mean()),
            2,
        ),
    }

    results["is_valid"] = all(
        [
            results["actual_rows"] == results["expected_rows"],
            results["null_opportunity_ids"] == 0,
            results["duplicated_opportunity_ids"] == 0,
            results["missing_accounts"] == 0,
            results["missing_stages"] == 0,
            results["negative_amounts"] == 0,
            results["negative_activity_counts"] == 0,
            results["negative_contact_counts"] == 0,
            results["invalid_activity_type_totals"] == 0,
            results["invalid_activity_flags"] == 0,
            results["invalid_contact_flags"] == 0,
            results["invalid_won_flags"] == 0,
            results["invalid_lost_flags"] == 0,
            results["invalid_closed_flags"] == 0,
            results["invalid_open_flags"] == 0,
            results["contradictory_open_closed_flags"] == 0,
            results["invalid_dates_still_present"] == 0,
            results["invalid_valid_date_orders"] == 0,
        ]
    )

    for rule_name, value in results.items():
        print(f"{rule_name}: {value}")

    if not results["is_valid"]:
        raise ValueError(
            "Gold crm_opportunity validation failed."
        )

    return results

def build_crm_lead_from_frames(
    leads: pd.DataFrame,
) -> pd.DataFrame:
    """Build one analytical row per CRM lead."""

    crm_lead = leads.rename(
        columns={
            "source": "lead_source",
            "status": "lead_status",
            "score": "lead_score",
        }
    ).copy()

    crm_lead["lead_name"] = (
        crm_lead["first_name"].astype("string")
        + " "
        + crm_lead["last_name"].astype("string")
    )

    crm_lead["is_new"] = (
        crm_lead["lead_status"].eq("new")
    )
    crm_lead["is_contacted"] = (
        crm_lead["lead_status"].eq("contacted")
    )
    crm_lead["is_qualified"] = (
        crm_lead["lead_status"].eq("qualified")
    )
    crm_lead["is_converted"] = (
        crm_lead["lead_status"].eq("converted")
    )
    crm_lead["is_lost"] = (
        crm_lead["lead_status"].eq("lost")
    )
    crm_lead["is_open"] = (
        crm_lead["lead_status"].isin(
            ["new", "contacted", "qualified"]
        )
    )
    crm_lead["is_closed"] = (
        crm_lead["lead_status"].isin(
            ["converted", "lost"]
        )
    )

    selected_columns = [
        "lead_id",
        "first_name",
        "last_name",
        "lead_name",
        "email",
        "lead_source",
        "lead_status",
        "lead_score",
        "created_at",
        "is_new",
        "is_contacted",
        "is_qualified",
        "is_converted",
        "is_lost",
        "is_open",
        "is_closed",
    ]

    return crm_lead[selected_columns].copy()


def build_crm_lead(
    silver_root: Path = SILVER_ROOT,
) -> pd.DataFrame:
    """Read Silver input and build Gold CRM leads."""

    return build_crm_lead_from_frames(
        leads=read_silver_table(
            "crm", "leads", silver_root
        ),
    )


def validate_crm_lead(
    dataframe: pd.DataFrame,
    expected_rows: int,
) -> dict[str, int | bool | float]:
    """Validate CRM-lead grain, score range and status flags."""

    expected_new_flag = dataframe["lead_status"].eq("new")
    expected_contacted_flag = dataframe["lead_status"].eq(
        "contacted"
    )
    expected_qualified_flag = dataframe["lead_status"].eq(
        "qualified"
    )
    expected_converted_flag = dataframe["lead_status"].eq(
        "converted"
    )
    expected_lost_flag = dataframe["lead_status"].eq("lost")
    expected_open_flag = dataframe["lead_status"].isin(
        ["new", "contacted", "qualified"]
    )
    expected_closed_flag = dataframe["lead_status"].isin(
        ["converted", "lost"]
    )

    status_flag_total = dataframe[
        [
            "is_new",
            "is_contacted",
            "is_qualified",
            "is_converted",
            "is_lost",
        ]
    ].sum(axis=1)

    converted_leads = int(dataframe["is_converted"].sum())
    total_leads = len(dataframe)

    results: dict[str, int | bool | float] = {
        "actual_rows": total_leads,
        "expected_rows": expected_rows,
        "null_lead_ids": int(
            dataframe["lead_id"].isna().sum()
        ),
        "duplicated_lead_ids": int(
            dataframe["lead_id"].duplicated().sum()
        ),
        "missing_sources": int(
            dataframe["lead_source"].isna().sum()
        ),
        "missing_statuses": int(
            dataframe["lead_status"].isna().sum()
        ),
        "missing_scores": int(
            dataframe["lead_score"].isna().sum()
        ),
        "missing_created_dates": int(
            dataframe["created_at"].isna().sum()
        ),
        "invalid_scores": int(
            (
                ~dataframe["lead_score"].between(0, 100)
            ).sum()
        ),
        "invalid_new_flags": int(
            dataframe["is_new"].ne(expected_new_flag).sum()
        ),
        "invalid_contacted_flags": int(
            dataframe["is_contacted"]
            .ne(expected_contacted_flag)
            .sum()
        ),
        "invalid_qualified_flags": int(
            dataframe["is_qualified"]
            .ne(expected_qualified_flag)
            .sum()
        ),
        "invalid_converted_flags": int(
            dataframe["is_converted"]
            .ne(expected_converted_flag)
            .sum()
        ),
        "invalid_lost_flags": int(
            dataframe["is_lost"].ne(expected_lost_flag).sum()
        ),
        "invalid_open_flags": int(
            dataframe["is_open"].ne(expected_open_flag).sum()
        ),
        "invalid_closed_flags": int(
            dataframe["is_closed"].ne(expected_closed_flag).sum()
        ),
        "invalid_status_flag_totals": int(
            status_flag_total.ne(1).sum()
        ),
        "contradictory_open_closed_flags": int(
            (
                dataframe["is_open"]
                & dataframe["is_closed"]
            ).sum()
        ),
        "new_leads": int(dataframe["is_new"].sum()),
        "contacted_leads": int(
            dataframe["is_contacted"].sum()
        ),
        "qualified_leads": int(
            dataframe["is_qualified"].sum()
        ),
        "converted_leads": converted_leads,
        "lost_leads": int(dataframe["is_lost"].sum()),
        "open_leads": int(dataframe["is_open"].sum()),
        "closed_leads": int(dataframe["is_closed"].sum()),
        "lead_source_count": int(
            dataframe["lead_source"].nunique()
        ),
        "average_lead_score": round(
            float(dataframe["lead_score"].mean()),
            2,
        ),
        "lead_conversion_rate": round(
            converted_leads / total_leads,
            4,
        ),
    }

    blocking_rules = [
        "actual_rows",
        "null_lead_ids",
        "duplicated_lead_ids",
        "missing_sources",
        "missing_statuses",
        "missing_scores",
        "missing_created_dates",
        "invalid_scores",
        "invalid_new_flags",
        "invalid_contacted_flags",
        "invalid_qualified_flags",
        "invalid_converted_flags",
        "invalid_lost_flags",
        "invalid_open_flags",
        "invalid_closed_flags",
        "invalid_status_flag_totals",
        "contradictory_open_closed_flags",
    ]

    results["is_valid"] = (
        results["actual_rows"] == results["expected_rows"]
        and all(
            results[rule_name] == 0
            for rule_name in blocking_rules[1:]
        )
    )

    for rule_name, value in results.items():
        print(f"{rule_name}: {value}")

    if not results["is_valid"]:
        raise ValueError(
            "Gold crm_lead validation failed."
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


def run_academic_performance(engine: Engine) -> None:
    """Build, validate, load and export academic performance."""

    table_name = "academic_performance"
    primary_key = "enrollment_id"

    print("\n" + "=" * 70)
    print("BUILDING GOLD.ACADEMIC_PERFORMANCE")
    print("=" * 70)

    expected_rows = len(
        read_silver_table("university", "enrollments")
    )
    dataframe = build_academic_performance()

    print("\n" + "=" * 70)
    print("VALIDATING GOLD.ACADEMIC_PERFORMANCE DATAFRAME")
    print("=" * 70)

    validate_academic_performance(
        dataframe,
        expected_rows,
    )

    print("\n" + "=" * 70)
    print("LOADING GOLD.ACADEMIC_PERFORMANCE INTO POSTGRESQL")
    print("=" * 70)

    load_gold_table(
        dataframe=dataframe,
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
        dataframe,
        table_name,
    )

    print("\n" + "=" * 70)
    print("GOLD.ACADEMIC_PERFORMANCE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"PostgreSQL table: {GOLD_SCHEMA}.{table_name}")
    print(f"Parquet export: {parquet_path}")


def run_invoice_financial(engine: Engine) -> None:
    """Build, validate, load and export invoice financial."""

    table_name = "invoice_financial"
    primary_key = "invoice_id"

    print("\n" + "=" * 70)
    print("BUILDING GOLD.INVOICE_FINANCIAL")
    print("=" * 70)

    expected_rows = len(
        read_silver_table("billing", "invoices")
    )
    dataframe = build_invoice_financial()

    print("\n" + "=" * 70)
    print("VALIDATING GOLD.INVOICE_FINANCIAL DATAFRAME")
    print("=" * 70)

    validate_invoice_financial(
        dataframe,
        expected_rows,
    )

    print("\n" + "=" * 70)
    print("LOADING GOLD.INVOICE_FINANCIAL INTO POSTGRESQL")
    print("=" * 70)

    load_gold_table(
        dataframe=dataframe,
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
        dataframe,
        table_name,
    )

    print("\n" + "=" * 70)
    print("GOLD.INVOICE_FINANCIAL COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"PostgreSQL table: {GOLD_SCHEMA}.{table_name}")
    print(f"Parquet export: {parquet_path}")



def run_product_sales(engine: Engine) -> None:
    """Build, validate, load and export product sales."""

    table_name = "product_sales"
    primary_key = "invoice_item_id"

    print("\n" + "=" * 70)
    print("BUILDING GOLD.PRODUCT_SALES")
    print("=" * 70)

    expected_rows = len(
        read_silver_table("billing", "invoice_items")
    )
    dataframe = build_product_sales()

    print("\n" + "=" * 70)
    print("VALIDATING GOLD.PRODUCT_SALES DATAFRAME")
    print("=" * 70)

    validate_product_sales(
        dataframe,
        expected_rows,
    )

    print("\n" + "=" * 70)
    print("LOADING GOLD.PRODUCT_SALES INTO POSTGRESQL")
    print("=" * 70)

    load_gold_table(
        dataframe=dataframe,
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
        dataframe,
        table_name,
    )

    print("\n" + "=" * 70)
    print("GOLD.PRODUCT_SALES COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"PostgreSQL table: {GOLD_SCHEMA}.{table_name}")
    print(f"Parquet export: {parquet_path}")


def run_subscription_portfolio(engine: Engine) -> None:
    """Build, validate, load and export subscription portfolio."""

    table_name = "subscription_portfolio"
    primary_key = "subscription_id"

    print("\n" + "=" * 70)
    print("BUILDING GOLD.SUBSCRIPTION_PORTFOLIO")
    print("=" * 70)

    expected_rows = len(
        read_silver_table("billing", "subscriptions")
    )
    dataframe = build_subscription_portfolio()

    print("\n" + "=" * 70)
    print("VALIDATING GOLD.SUBSCRIPTION_PORTFOLIO DATAFRAME")
    print("=" * 70)

    validate_subscription_portfolio(
        dataframe,
        expected_rows,
    )

    print("\n" + "=" * 70)
    print("LOADING GOLD.SUBSCRIPTION_PORTFOLIO INTO POSTGRESQL")
    print("=" * 70)

    load_gold_table(
        dataframe=dataframe,
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
        dataframe,
        table_name,
    )

    print("\n" + "=" * 70)
    print("GOLD.SUBSCRIPTION_PORTFOLIO COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"PostgreSQL table: {GOLD_SCHEMA}.{table_name}")
    print(f"Parquet export: {parquet_path}")


def run_crm_opportunity(engine: Engine) -> None:
    """Build, validate, load and export CRM opportunities."""

    table_name = "crm_opportunity"
    primary_key = "opportunity_id"

    print("\n" + "=" * 70)
    print("BUILDING GOLD.CRM_OPPORTUNITY")
    print("=" * 70)

    expected_rows = len(
        read_silver_table("crm", "opportunities")
    )
    dataframe = build_crm_opportunity()

    print("\n" + "=" * 70)
    print("VALIDATING GOLD.CRM_OPPORTUNITY DATAFRAME")
    print("=" * 70)

    validate_crm_opportunity(
        dataframe,
        expected_rows,
    )

    print("\n" + "=" * 70)
    print("LOADING GOLD.CRM_OPPORTUNITY INTO POSTGRESQL")
    print("=" * 70)

    load_gold_table(
        dataframe=dataframe,
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
        dataframe,
        table_name,
    )

    print("\n" + "=" * 70)
    print("GOLD.CRM_OPPORTUNITY COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"PostgreSQL table: {GOLD_SCHEMA}.{table_name}")
    print(f"Parquet export: {parquet_path}")

def run_crm_lead(engine: Engine) -> None:
    """Build, validate, load and export CRM leads."""

    table_name = "crm_lead"
    primary_key = "lead_id"

    print("\n" + "=" * 70)
    print("BUILDING GOLD.CRM_LEAD")
    print("=" * 70)

    expected_rows = len(
        read_silver_table("crm", "leads")
    )
    dataframe = build_crm_lead()

    print("\n" + "=" * 70)
    print("VALIDATING GOLD.CRM_LEAD DATAFRAME")
    print("=" * 70)

    validate_crm_lead(
        dataframe,
        expected_rows,
    )

    print("\n" + "=" * 70)
    print("LOADING GOLD.CRM_LEAD INTO POSTGRESQL")
    print("=" * 70)

    load_gold_table(
        dataframe=dataframe,
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
        dataframe,
        table_name,
    )

    print("\n" + "=" * 70)
    print("GOLD.CRM_LEAD COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"PostgreSQL table: {GOLD_SCHEMA}.{table_name}")
    print(f"Parquet export: {parquet_path}")

def main() -> None:
    """Build, validate, load and export all implemented Gold tables."""

    engine = get_postgres_engine()

    run_academic_performance(engine)
    run_invoice_financial(engine)
    run_product_sales(engine)
    run_subscription_portfolio(engine)
    run_crm_opportunity(engine)
    run_crm_lead(engine)

    print("\n" + "=" * 70)
    print("GOLD PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
