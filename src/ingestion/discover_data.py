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


def analyze_dataframe(dataframe: pd.DataFrame) -> dict:
    """Return basic information about a DataFrame."""
    return {
        "rows": dataframe.shape[0],
        "columns": dataframe.shape[1],
    }


def main() -> None:
      project_root = Path(__file__).resolve().parents[2]
      raw_data_path = project_root / "data" / "raw"

      csv_files = find_csv_files(raw_data_path)

      print(f"CSV files found: {len(csv_files)}")

      for csv_file in csv_files:
            dataframe = load_csv(csv_file)
            analysis = analyze_dataframe(dataframe)

            print(f"\nFile: {csv_file.relative_to(project_root)}")
            print(f"Rows: {analysis['rows']}")
            print(f"Columns: {analysis['columns']}")


if __name__ == "__main__":
    main()