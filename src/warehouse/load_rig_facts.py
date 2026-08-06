from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config.database import get_engine


PARQUET_FILE = Path(
    "data/processed/rig_count/rig_count.parquet"
)


def read_parquet() -> pd.DataFrame:
    if not PARQUET_FILE.exists():
        raise FileNotFoundError(
            f"Rig-count Parquet not found: "
            f"{PARQUET_FILE.resolve()}"
        )

    df = pd.read_parquet(PARQUET_FILE)

    df["observation_date"] = pd.to_datetime(
        df["observation_date"],
        errors="coerce",
    )

    df["rig_count"] = pd.to_numeric(
        df["rig_count"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "observation_date",
            "country",
            "drilling_target",
            "location_type",
            "rig_status",
            "rig_count",
            "source",
            "source_file",
            "ingestion_time",
        ]
    )

    df = df[df["rig_count"] >= 0]

    df = df.drop_duplicates(
        subset=[
            "observation_date",
            "country",
            "drilling_target",
            "location_type",
            "rig_status",
            "source",
        ],
        keep="last",
    )

    if df.empty:
        raise ValueError(
            "No valid rig-count fact rows remain."
        )

    return df.reset_index(drop=True)


def get_time_mapping(
    connection: Connection,
) -> dict[pd.Timestamp, int]:
    rows = connection.execute(
        text(
            """
            SELECT time_key, timestamp
            FROM dim_time;
            """
        )
    ).mappings()

    return {
        pd.Timestamp(row["timestamp"]):
            int(row["time_key"])
        for row in rows
    }


def get_country_mapping(
    connection: Connection,
) -> dict[str, int]:
    rows = connection.execute(
        text(
            """
            SELECT country_key, country_name
            FROM dim_country;
            """
        )
    ).mappings()

    return {
        str(row["country_name"]).strip().upper():
            int(row["country_key"])
        for row in rows
    }


def get_classification_mapping(
    connection: Connection,
) -> dict[tuple[str, str, str], int]:
    rows = connection.execute(
        text(
            """
            SELECT
                rig_classification_key,
                drilling_target,
                location_type,
                rig_status
            FROM dim_rig_classification;
            """
        )
    ).mappings()

    return {
        (
            str(row["drilling_target"]).strip().title(),
            str(row["location_type"]).strip().title(),
            str(row["rig_status"]).strip().title(),
        ): int(row["rig_classification_key"])
        for row in rows
    }


def build_records(
    dataframe: pd.DataFrame,
    time_mapping: dict[pd.Timestamp, int],
    country_mapping: dict[str, int],
    classification_mapping:
        dict[tuple[str, str, str], int],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row in dataframe.itertuples(index=False):
        timestamp = pd.Timestamp(
            row.observation_date
        )

        country_name = str(
            row.country
        ).strip().upper()

        classification = (
            str(row.drilling_target).strip().title(),
            str(row.location_type).strip().title(),
            str(row.rig_status).strip().title(),
        )

        time_key = time_mapping.get(timestamp)
        country_key = country_mapping.get(
            country_name
        )
        classification_key = (
            classification_mapping.get(
                classification
            )
        )

        if time_key is None:
            raise KeyError(
                f"No time_key for {timestamp}"
            )

        if country_key is None:
            raise KeyError(
                f"No country_key for {country_name}"
            )

        if classification_key is None:
            raise KeyError(
                "No classification key for "
                f"{classification}"
            )

        records.append(
            {
                "time_key":
                    time_key,

                "country_key":
                    country_key,

                "rig_classification_key":
                    classification_key,

                "rig_count":
                    float(row.rig_count),

                "source":
                    str(row.source).strip(),

                "source_file":
                    str(row.source_file).strip(),

                "source_ingestion_time":
                    pd.Timestamp(
                        row.ingestion_time
                    ).to_pydatetime(),
            }
        )

    return records


def load_records(
    connection: Connection,
    records: list[dict[str, Any]],
) -> int:
    upsert_sql = text(
        """
        INSERT INTO fact_rig_count
        (
            time_key,
            country_key,
            rig_classification_key,
            rig_count,
            source,
            source_file,
            source_ingestion_time
        )
        VALUES
        (
            :time_key,
            :country_key,
            :rig_classification_key,
            :rig_count,
            :source,
            :source_file,
            :source_ingestion_time
        )
        ON CONFLICT
        (
            time_key,
            country_key,
            rig_classification_key,
            source
        )
        DO UPDATE SET
            rig_count =
                EXCLUDED.rig_count,
            source_file =
                EXCLUDED.source_file,
            source_ingestion_time =
                EXCLUDED.source_ingestion_time,
            warehouse_loaded_at =
                CURRENT_TIMESTAMP;
        """
    )

    connection.execute(
        upsert_sql,
        records,
    )

    logger.success(
        "fact_rig_count processed: {} rows",
        len(records),
    )

    return len(records)


def load_rig_facts() -> int:
    logger.info(
        "Starting rig-count fact loading"
    )

    dataframe = read_parquet()

    engine = get_engine()

    with engine.begin() as connection:
        time_mapping = get_time_mapping(
            connection
        )

        country_mapping = get_country_mapping(
            connection
        )

        classification_mapping = (
            get_classification_mapping(
                connection
            )
        )

        records = build_records(
            dataframe,
            time_mapping,
            country_mapping,
            classification_mapping,
        )

        loaded_rows = load_records(
            connection,
            records,
        )

    logger.success(
        "Rig-count fact loading completed"
    )

    return loaded_rows


def main() -> None:
    load_rig_facts()


if __name__ == "__main__":
    main()