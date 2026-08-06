from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from loguru import logger


BRONZE_FOLDER = Path(
    "data/raw/rig_count/bronze"
)

MANUAL_FOLDER = Path(
    "data/raw/rig_count/manual"
)

OUTPUT_FILE = Path(
    "data/processed/rig_count/rig_count.parquet"
)

SHEET_NAME = "WW Monthly"

HEADER_ROW = 11


class RigCountTransformer:
    """
    Transform the Baker Hughes Worldwide Monthly
    rig-count workbook into a standardized Silver
    Parquet dataset.
    """

    REQUIRED_SOURCE_COLUMNS = {
        "Region",
        "Country",
        "DrillFor",
        "Location",
        "Rig Status",
        "Year",
        "Month",
        "Rig Count Value",
    }

    def get_latest_workbook(self) -> Path:
        """
        Select the newest valid Excel workbook.

        Bronze is preferred. The manual folder is used
        as a fallback while developing the pipeline.
        """

        search_folders = [
            BRONZE_FOLDER,
            MANUAL_FOLDER,
        ]

        files: list[Path] = []

        for folder in search_folders:
            if folder.exists():
                files.extend(
                    file
                    for file in folder.rglob("*.xlsx")
                    if (
                        file.is_file()
                        and file.stat().st_size > 0
                    )
                )

        if not files:
            raise FileNotFoundError(
                "No valid rig-count workbook found under "
                f"{BRONZE_FOLDER.resolve()} or "
                f"{MANUAL_FOLDER.resolve()}."
            )

        latest_file = max(
            files,
            key=lambda file: file.stat().st_mtime,
        )

        logger.info(
            "Selected rig-count workbook: {}",
            latest_file,
        )

        return latest_file

    @staticmethod
    def read_monthly_sheet(
        workbook: Path,
    ) -> pd.DataFrame:
        """
        Read the detailed WW Monthly table.

        The workbook header appears on worksheet row 12,
        therefore pandas uses header=11.
        """

        logger.info(
            "Reading sheet '{}' from {}",
            SHEET_NAME,
            workbook,
        )

        dataframe = pd.read_excel(
            workbook,
            sheet_name=SHEET_NAME,
            header=HEADER_ROW,
            engine="openpyxl",
        )

        logger.info(
            "Raw monthly columns: {}",
            dataframe.columns.tolist(),
        )

        return dataframe

    def validate_source_schema(
        self,
        dataframe: pd.DataFrame,
    ) -> None:
        missing_columns = (
            self.REQUIRED_SOURCE_COLUMNS
            - set(dataframe.columns)
        )

        if missing_columns:
            raise ValueError(
                "Rig-count workbook is missing columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

    @staticmethod
    def clean_text_column(
        series: pd.Series,
    ) -> pd.Series:
        return (
            series
            .astype("string")
            .str.strip()
        )

    def transform(
        self,
        source_df: pd.DataFrame,
        source_file: Path,
    ) -> pd.DataFrame:
        """
        Standardize Baker Hughes source columns.
        """

        logger.info(
            "Transforming Baker Hughes monthly rig-count data"
        )

        self.validate_source_schema(source_df)

        df = source_df[
            [
                "Region",
                "Country",
                "DrillFor",
                "Location",
                "Rig Status",
                "Year",
                "Month",
                "Rig Count Value",
            ]
        ].copy()

        text_columns = [
            "Region",
            "Country",
            "DrillFor",
            "Location",
            "Rig Status",
        ]

        for column in text_columns:
            df[column] = self.clean_text_column(
                df[column]
            )

        df["Year"] = pd.to_numeric(
            df["Year"],
            errors="coerce",
        )

        df["Month"] = pd.to_numeric(
            df["Month"],
            errors="coerce",
        )

        df["Rig Count Value"] = pd.to_numeric(
            df["Rig Count Value"],
            errors="coerce",
        )

        rows_before_cleanup = len(df)

        df = df.dropna(
            subset=[
                "Region",
                "Country",
                "DrillFor",
                "Location",
                "Rig Status",
                "Year",
                "Month",
                "Rig Count Value",
            ]
        )

        df = df[
            df["Month"].between(1, 12)
        ]

        df = df[
            df["Year"].between(1900, 2100)
        ]

        df = df[
            df["Rig Count Value"] >= 0
        ]

        df["Year"] = df["Year"].astype(int)
        df["Month"] = df["Month"].astype(int)

        df["observation_date"] = pd.to_datetime(
            {
                "year": df["Year"],
                "month": df["Month"],
                "day": 1,
            },
            errors="coerce",
        )

        df = df.dropna(
            subset=["observation_date"]
        )

        ingestion_time = datetime.now(
            timezone.utc
        ).replace(tzinfo=None)

        silver_df = pd.DataFrame(
            {
                "observation_date":
                    df["observation_date"],

                "region":
                    df["Region"],

                "country":
                    df["Country"],

                "drilling_target":
                    df["DrillFor"],

                "location_type":
                    df["Location"],

                "rig_status":
                    df["Rig Status"],

                "rig_count":
                    df["Rig Count Value"],

                "source":
                    "Baker Hughes",

                "source_file":
                    source_file.name,

                "ingestion_time":
                    ingestion_time,
            }
        )

        silver_df["region"] = (
            silver_df["region"]
            .str.title()
        )

        silver_df["country"] = (
            silver_df["country"]
            .str.upper()
        )

        silver_df["drilling_target"] = (
            silver_df["drilling_target"]
            .str.title()
        )

        silver_df["location_type"] = (
            silver_df["location_type"]
            .str.title()
        )

        silver_df["rig_status"] = (
            silver_df["rig_status"]
            .str.title()
        )

        silver_df = silver_df.drop_duplicates(
            subset=[
                "observation_date",
                "country",
                "drilling_target",
                "location_type",
                "rig_status",
            ],
            keep="last",
        )

        silver_df = silver_df.sort_values(
            by=[
                "observation_date",
                "region",
                "country",
                "drilling_target",
                "location_type",
            ]
        ).reset_index(drop=True)

        removed_rows = (
            rows_before_cleanup
            - len(silver_df)
        )

        if removed_rows > 0:
            logger.warning(
                "Removed {} invalid, empty, or duplicate rows",
                removed_rows,
            )

        if silver_df.empty:
            raise ValueError(
                "Rig-count transformation produced no valid rows."
            )

        logger.success(
            "Rig-count transformation completed: {} rows",
            len(silver_df),
        )

        return silver_df

    @staticmethod
    def save_parquet(
        dataframe: pd.DataFrame,
    ) -> Path:
        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        dataframe.to_parquet(
            OUTPUT_FILE,
            index=False,
        )

        logger.success(
            "Rig-count Silver Parquet saved: {}",
            OUTPUT_FILE,
        )

        return OUTPUT_FILE

    def execute(self) -> Path:
        workbook = self.get_latest_workbook()

        source_df = self.read_monthly_sheet(
            workbook
        )

        silver_df = self.transform(
            source_df,
            workbook,
        )

        output_file = self.save_parquet(
            silver_df
        )

        print("\nSilver columns:")
        print(silver_df.columns.tolist())

        print("\nSilver preview:")
        print(
            silver_df.head(10).to_string(
                index=False
            )
        )

        print("\nSilver data types:")
        print(silver_df.dtypes)

        return output_file


def main() -> None:
    transformer = RigCountTransformer()
    transformer.execute()


if __name__ == "__main__":
    main()