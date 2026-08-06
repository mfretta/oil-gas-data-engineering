from pathlib import Path
import json

import pandas as pd
from loguru import logger


class OilPriceTransformer:
    """
    Transform raw EIA oil-market JSON into a standardized
    Silver-layer Parquet dataset.
    """

    REQUIRED_SOURCE_COLUMNS = {
        "period",
        "product",
        "product-name",
        "value",
        "series",
    }

    def __init__(self) -> None:
        self.raw_folder = Path(
            "data/raw/oil_prices"
        )

        self.output_folder = Path(
            "data/processed/oil_prices"
        )

        self.output_file = (
            self.output_folder
            / "oil_prices.parquet"
        )

        self.output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get_latest_json(self) -> Path:
        """
        Return the most recently modified raw JSON file.
        """

        files = list(
            self.raw_folder.rglob("*.json")
        )

        if not files:
            raise FileNotFoundError(
                f"No raw JSON files found in: "
                f"{self.raw_folder.resolve()}"
            )

        latest_file = max(
            files,
            key=lambda file: file.stat().st_mtime,
        )

        logger.info(
            "Latest raw file selected: {}",
            latest_file,
        )

        return latest_file

    @staticmethod
    def load_json(file_path: Path) -> dict:
        """
        Load a raw EIA JSON response.
        """

        logger.info(
            "Loading raw JSON: {}",
            file_path,
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    @staticmethod
    def extract_records(
        data: dict,
    ) -> list[dict]:
        """
        Extract records from the EIA response structure.
        """

        records = (
            data
            .get("response", {})
            .get("data", [])
        )

        if not records:
            raise ValueError(
                "No records found in "
                "data['response']['data']."
            )

        return records

    def transform(
        self,
        data: dict,
    ) -> pd.DataFrame:
        """
        Transform EIA-specific fields into a standardized
        Silver-layer schema.
        """

        logger.info(
            "Transforming EIA oil-price data"
        )

        records = self.extract_records(data)

        source_df = pd.DataFrame(records)

        logger.info(
            "Source columns: {}",
            source_df.columns.tolist(),
        )

        missing_columns = (
            self.REQUIRED_SOURCE_COLUMNS
            - set(source_df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Missing required source columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        if "units" in source_df.columns:
            units = source_df["units"]
        else:
            units = pd.Series(
                ["UNKNOWN"] * len(source_df),
                index=source_df.index,
            )

        silver_df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    source_df["period"],
                    errors="coerce",
                ),
                "product_code": (
                    source_df["product"]
                    .astype("string")
                    .str.strip()
                ),
                "product": (
                    source_df["product-name"]
                    .astype("string")
                    .str.strip()
                ),
                "price_usd": pd.to_numeric(
                    source_df["value"],
                    errors="coerce",
                ),
                "unit": (
                    units
                    .astype("string")
                    .str.strip()
                ),
                "source": "EIA",
                "series": (
                    source_df["series"]
                    .astype("string")
                    .str.strip()
                ),
            }
        )

        optional_column_mapping = {
            "duoarea": "area_code",
            "area-name": "area_name",
            "process": "process_code",
            "process-name": "process_name",
            "series-description":
                "series_description",
        }

        for (
            source_column,
            target_column,
        ) in optional_column_mapping.items():

            if source_column in source_df.columns:
                silver_df[target_column] = (
                    source_df[source_column]
                    .astype("string")
                    .str.strip()
                )

        rows_before_cleanup = len(silver_df)

        silver_df = silver_df.dropna(
            subset=[
                "timestamp",
                "product_code",
                "product",
                "price_usd",
                "unit",
                "source",
                "series",
            ]
        )

        silver_df = silver_df[
            silver_df["price_usd"] >= 0
        ]

        silver_df = silver_df.drop_duplicates(
            subset=[
                "timestamp",
                "series",
            ],
            keep="last",
        )

        silver_df = silver_df.sort_values(
            by=[
                "timestamp",
                "series",
            ]
        ).reset_index(drop=True)

        removed_rows = (
            rows_before_cleanup
            - len(silver_df)
        )

        if removed_rows > 0:
            logger.warning(
                "Removed {} invalid or duplicate rows",
                removed_rows,
            )

        if silver_df.empty:
            raise ValueError(
                "Transformation produced no valid rows."
            )

        logger.success(
            "Transformation completed: {} rows",
            len(silver_df),
        )

        return silver_df

    def save_parquet(
        self,
        dataframe: pd.DataFrame,
    ) -> Path:
        """
        Save the standardized Silver dataset.
        """

        dataframe.to_parquet(
            self.output_file,
            index=False,
        )

        logger.success(
            "Saved Silver Parquet: {}",
            self.output_file,
        )

        return self.output_file

    def execute(self) -> Path:
        """
        Execute the complete Bronze-to-Silver process.
        """

        raw_file = self.get_latest_json()

        data = self.load_json(raw_file)

        dataframe = self.transform(data)

        output_file = self.save_parquet(
            dataframe
        )

        print("\nSilver columns:")
        print(dataframe.columns.tolist())

        print("\nSilver preview:")
        print(
            dataframe.head().to_string(
                index=False
            )
        )

        return output_file


def main() -> None:
    transformer = OilPriceTransformer()
    transformer.execute()


if __name__ == "__main__":
    main()