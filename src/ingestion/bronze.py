from pathlib import Path

from src.ingestion.discover_data import find_csv_files, load_csv


import pandas as pd

def build_bronze_path(
    raw_path: Path,
    raw_root: Path,
    bronze_root: Path,
) -> Path:
    """Build the Bronze Parquet path from a Raw CSV path."""

    relative_path = raw_path.relative_to(raw_root)

    return (
        bronze_root
        / relative_path
    ).with_suffix(".parquet")
   

def save_as_parquet(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save a DataFrame as a Parquet file."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe.to_parquet(
        output_path,
        index=False,
        engine="pyarrow",
    )

def process_bronze_file(
    raw_path: Path,
    raw_root: Path,
    bronze_root: Path,
) -> Path:
    """Load one Raw CSV file and save it in Bronze as Parquet."""

    dataframe = load_csv(raw_path)

    bronze_path = build_bronze_path(
        raw_path,
        raw_root,
        bronze_root,
    )

    save_as_parquet(
        dataframe,
        bronze_path,
    )

    return bronze_path

def run_bronze_ingestion(
    csv_files: list[Path],
    raw_root: Path,
    bronze_root: Path,
) -> None:
    """Process all Raw CSV files into Bronze Parquet files."""

    for csv_file in csv_files:
        bronze_path = process_bronze_file(
            csv_file,
            raw_root,
            bronze_root,
        )

        print(f"Created: {bronze_path}")

def validate_bronze_file(
    raw_path: Path,
    bronze_path: Path,
) -> bool:
    """Validate that Raw and Bronze have the same shape."""

    raw_df = load_csv(raw_path)
    bronze_df = pd.read_parquet(bronze_path)

    print(f"Raw shape: {raw_df.shape}")
    print(f"Bronze shape: {bronze_df.shape}")

    return raw_df.shape == bronze_df.shape


def main():
    raw_root = Path("data/raw")
    bronze_root = Path("data/bronze")

    csv_files = find_csv_files(raw_root)

    run_bronze_ingestion(
        csv_files,
        raw_root,
        bronze_root,
    )



if __name__ == "__main__":
    main()