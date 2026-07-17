from pathlib import Path

import pandas as pd

def find_csv_files(base_path: Path) -> list[Path]:
    """Find all CSV files recursively inside the given directory."""
    return list(base_path.rglob("*.csv"))


def load_csv(csv_path: Path) -> pd.DataFrame:
    """
    Load a CSV file into a pandas DataFrame.
    """
    return pd.read_csv(csv_path)

def get_shape(dataframe: pd.DataFrame) -> dict:
    """Return the number of rows and columns in a DataFrame."""
    return {
        "rows": dataframe.shape[0],
        "columns": dataframe.shape[1],
    }
def get_column_types(dataframe: pd.DataFrame) -> dict:
    """Return the detected data type of each DataFrame column."""
    return {
        "column_types": {
            column: str(dtype)
            for column, dtype in dataframe.dtypes.items()
        }
    }


def get_missing_values(dataframe: pd.DataFrame) -> dict:
    """Return the number of missing values for each column."""
    return {
        "missing_values": dataframe.isna().sum().to_dict()
    }


def get_duplicate_rows(dataframe: pd.DataFrame) -> dict:
    """Return the number of completely duplicated rows."""
    return {
        "duplicate_rows": int(dataframe.duplicated().sum())
    }

def get_unique_values(dataframe: pd.DataFrame) -> dict:
    """Return the number of unique non-null values for each column."""
    return {
        "unique_values": dataframe.nunique(dropna=True).to_dict()
    }


def analyze_dataframe(dataframe: pd.DataFrame) -> dict:
    """Coordinate the DataFrame profiling functions."""
    analysis = {}
    analysis.update(get_shape(dataframe))
    analysis.update(get_column_types(dataframe))
    analysis.update(get_missing_values(dataframe))
    analysis.update(get_duplicate_rows(dataframe))
    analysis.update(get_unique_values(dataframe))

    return analysis


def print_analysis_report(csv_file: Path, analysis: dict) -> None:
    print("\n" + "=" * 60)
    print(f"Domain : {csv_file.parent.name.capitalize()}")
    print(f"File   : {csv_file.name}")
    print("=" * 60)

    print(f"Rows    : {analysis['rows']}")
    print(f"Columns : {analysis['columns']}")

    print("\nColumn Types")
    print("-" * 30)

    for column, dtype in analysis["column_types"].items():
        print(f"{column:<20} {dtype}")
    print("\nMissing Values")
    print("-" * 30)

    has_missing = False

    for column, missing in analysis["missing_values"].items():
        if missing > 0:
            print(f"{column:<20} {missing}")
            has_missing = True

    if not has_missing:
        print("No missing values")

    print("\nDuplicate Rows")
    print("-" * 30)
    print(analysis["duplicate_rows"])



def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    raw_data_path = project_root / "data" / "raw"

    csv_files = find_csv_files(raw_data_path)

    print(f"CSV files found: {len(csv_files)}")

    for csv_file in csv_files:
        dataframe = load_csv(csv_file)
        analysis = analyze_dataframe(dataframe)

        print_analysis_report(csv_file, analysis)


if __name__ == "__main__":
    main()