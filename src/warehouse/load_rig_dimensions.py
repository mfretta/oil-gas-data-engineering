from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


PARQUET_FILE = Path(
    "data/processed/rig_count/rig_count.parquet"
)


REQUIRED_COLUMNS = {
    "observation_date",
    "region",
    "country",
    "drilling_target",
    "location_type",
    "rig_status",
    "rig_count",
    "source",
    "source_file",
    "ingestion_time",
}


def read_rig_count_parquet() -> pd.DataFrame:
    if not PARQUET_FILE.exists():
        raise FileNotFoundError(
            f"Rig-count Parquet not found: "
            f"{PARQUET_FILE.resolve()}"
        )

    logger.info(
        "Reading rig-count Silver Parquet: {}",
        PARQUET_FILE,
    )

    df = pd.read_parquet(PARQUET_FILE)

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            "Missing required rig-count columns: "
            + ", ".join(sorted(missing))
        )

    if df.empty:
        raise ValueError(
            "Rig-count Silver Parquet is empty."
        )

    df["observation_date"] = pd.to_datetime(
        df["observation_date"],
        errors="coerce",
    )

    string_columns = [
        "region",
        "country",
        "drilling_target",
        "location_type",
        "rig_status",
    ]

    for column in string_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    df = df.dropna(
        subset=[
            "observation_date",
            "region",
            "country",
            "drilling_target",
            "location_type",
            "rig_status",
        ]
    )

    if df.empty:
        raise ValueError(
            "No valid rig-count rows remain."
        )

    logger.success(
        "Rig-count Parquet validated: {} rows",
        len(df),
    )

    return df.reset_index(drop=True)


def get_season(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"

    if month in (3, 4, 5):
        return "Spring"

    if month in (6, 7, 8):
        return "Summer"

    return "Autumn"


def load_dim_time(df: pd.DataFrame) -> int:
    timestamps = (
        df["observation_date"]
        .drop_duplicates()
        .sort_values()
    )

    insert_sql = text(
        """
        INSERT INTO dim_time
        (
            timestamp,
            date,
            hour,
            month,
            season
        )
        VALUES
        (
            :timestamp,
            :date,
            :hour,
            :month,
            :season
        )
        ON CONFLICT (timestamp)
        DO NOTHING;
        """
    )

    engine = get_engine()

    with engine.begin() as connection:
        for value in timestamps:
            timestamp = pd.Timestamp(value)

            connection.execute(
                insert_sql,
                {
                    "timestamp":
                        timestamp.to_pydatetime(),
                    "date":
                        timestamp.date(),
                    "hour":
                        0,
                    "month":
                        int(timestamp.month),
                    "season":
                        get_season(
                            int(timestamp.month)
                        ),
                },
            )

    logger.success(
        "dim_time processed for rig count: {} dates",
        len(timestamps),
    )

    return len(timestamps)


def load_dim_country(df: pd.DataFrame) -> int:
    countries = (
        df[
            [
                "country",
                "region",
            ]
        ]
        .drop_duplicates()
        .to_dict("records")
    )

    upsert_sql = text(
        """
        INSERT INTO dim_country
        (
            country_name,
            region
        )
        VALUES
        (
            :country_name,
            :region
        )
        ON CONFLICT (country_name)
        DO UPDATE SET
            region = EXCLUDED.region,
            updated_at = CURRENT_TIMESTAMP;
        """
    )

    engine = get_engine()

    with engine.begin() as connection:
        for row in countries:
            connection.execute(
                upsert_sql,
                {
                    "country_name":
                        str(row["country"]).strip().upper(),
                    "region":
                        str(row["region"]).strip().title(),
                },
            )

    logger.success(
        "dim_country processed: {} countries",
        len(countries),
    )

    return len(countries)


def load_dim_rig_classification(
    df: pd.DataFrame,
) -> int:
    classifications = (
        df[
            [
                "drilling_target",
                "location_type",
                "rig_status",
            ]
        ]
        .drop_duplicates()
        .to_dict("records")
    )

    upsert_sql = text(
        """
        INSERT INTO dim_rig_classification
        (
            drilling_target,
            location_type,
            rig_status
        )
        VALUES
        (
            :drilling_target,
            :location_type,
            :rig_status
        )
        ON CONFLICT
        (
            drilling_target,
            location_type,
            rig_status
        )
        DO UPDATE SET
            updated_at = CURRENT_TIMESTAMP;
        """
    )

    engine = get_engine()

    with engine.begin() as connection:
        for row in classifications:
            connection.execute(
                upsert_sql,
                {
                    "drilling_target":
                        str(
                            row["drilling_target"]
                        ).strip().title(),

                    "location_type":
                        str(
                            row["location_type"]
                        ).strip().title(),

                    "rig_status":
                        str(
                            row["rig_status"]
                        ).strip().title(),
                },
            )

    logger.success(
        "dim_rig_classification processed: {} rows",
        len(classifications),
    )

    return len(classifications)


def load_rig_dimensions() -> None:
    logger.info(
        "Starting rig-count dimension loading"
    )

    dataframe = read_rig_count_parquet()

    load_dim_time(dataframe)

    load_dim_country(dataframe)

    load_dim_rig_classification(dataframe)

    logger.success(
        "Rig-count dimensions loaded successfully"
    )


def main() -> None:
    load_rig_dimensions()


if __name__ == "__main__":
    main()