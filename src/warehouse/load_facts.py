from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config.database import get_engine


PARQUET_FILE = Path(
    "data/processed/oil_prices/oil_prices.parquet"
)


REQUIRED_COLUMNS = {
    "timestamp",
    "product_code",
    "product",
    "price_usd",
    "unit",
    "source",
    "series",
}


def read_oil_price_parquet() -> pd.DataFrame:
    """
    Read and validate the standardized Silver Parquet.
    """

    if not PARQUET_FILE.exists():
        raise FileNotFoundError(
            f"Parquet file not found: "
            f"{PARQUET_FILE.resolve()}"
        )

    logger.info(
        "Reading Silver oil-price Parquet: {}",
        PARQUET_FILE,
    )

    df = pd.read_parquet(PARQUET_FILE)

    missing_columns = (
        REQUIRED_COLUMNS - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    if df.empty:
        raise ValueError(
            "Oil-price Parquet contains no records."
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["price_usd"] = pd.to_numeric(
        df["price_usd"],
        errors="coerce",
    )

    string_columns = [
        "product_code",
        "product",
        "unit",
        "source",
        "series",
    ]

    for column in string_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    df["product_code"] = (
        df["product_code"]
        .str.upper()
    )

    df = df.dropna(
        subset=[
            "timestamp",
            "product_code",
            "price_usd",
            "unit",
            "source",
            "series",
        ]
    )

    df = df[df["price_usd"] >= 0]

    df = df.drop_duplicates(
        subset=[
            "timestamp",
            "product_code",
            "source",
            "series",
        ],
        keep="last",
    )

    if df.empty:
        raise ValueError(
            "No valid fact rows remain after validation."
        )

    logger.success(
        "Fact source validated: {} rows",
        len(df),
    )

    return df.reset_index(drop=True)


def get_time_mapping(
    connection: Connection,
    dataframe: pd.DataFrame,
) -> dict[pd.Timestamp, int]:
    """
    Resolve timestamps to dim_time surrogate keys.
    """

    timestamps = [
        pd.Timestamp(timestamp).to_pydatetime()
        for timestamp in (
            dataframe["timestamp"]
            .drop_duplicates()
            .tolist()
        )
    ]

    query = text(
        """
        SELECT
            time_key,
            timestamp
        FROM dim_time
        WHERE timestamp = ANY(:timestamps);
        """
    )

    rows = connection.execute(
        query,
        {
            "timestamps": timestamps,
        },
    ).mappings()

    mapping = {
        pd.Timestamp(row["timestamp"]):
            int(row["time_key"])
        for row in rows
    }

    missing_timestamps = (
        set(pd.Timestamp(value) for value in timestamps)
        - set(mapping)
    )

    if missing_timestamps:
        examples = sorted(
            missing_timestamps
        )[:5]

        raise ValueError(
            "Some timestamps were not found in dim_time. "
            f"Examples: {examples}. "
            "Run load_dimensions first."
        )

    logger.info(
        "Resolved {} time keys",
        len(mapping),
    )

    return mapping


def get_product_mapping(
    connection: Connection,
    dataframe: pd.DataFrame,
) -> dict[str, int]:
    """
    Resolve EIA product codes to dimension surrogate keys.
    """

    product_codes = (
        dataframe["product_code"]
        .drop_duplicates()
        .tolist()
    )

    query = text(
        """
        SELECT
            product_key,
            product_code
        FROM dim_energy_product
        WHERE product_code = ANY(:product_codes);
        """
    )

    rows = connection.execute(
        query,
        {
            "product_codes": product_codes,
        },
    ).mappings()

    mapping = {
        str(row["product_code"]).strip().upper():
            int(row["product_key"])
        for row in rows
    }

    missing_products = (
        set(product_codes)
        - set(mapping)
    )

    if missing_products:
        raise ValueError(
            "Some products were not found in "
            "dim_energy_product: "
            + ", ".join(
                sorted(missing_products)
            )
            + ". Run load_dimensions first."
        )

    logger.info(
        "Resolved {} product keys",
        len(mapping),
    )

    return mapping


def build_fact_records(
    dataframe: pd.DataFrame,
    time_mapping: dict[pd.Timestamp, int],
    product_mapping: dict[str, int],
) -> list[dict[str, Any]]:
    """
    Convert Silver records into warehouse fact records.
    """

    records: list[dict[str, Any]] = []

    for row in dataframe.itertuples(
        index=False
    ):
        timestamp = pd.Timestamp(
            row.timestamp
        )

        product_code = str(
            row.product_code
        ).strip().upper()

        time_key = time_mapping.get(
            timestamp
        )

        product_key = product_mapping.get(
            product_code
        )

        if time_key is None:
            raise KeyError(
                f"time_key not found for {timestamp}"
            )

        if product_key is None:
            raise KeyError(
                "product_key not found for "
                f"{product_code}"
            )

        records.append(
            {
                "time_key": time_key,
                "product_key": product_key,
                "price_usd": float(
                    row.price_usd
                ),
                "unit": str(
                    row.unit
                ).strip(),
                "source": str(
                    row.source
                ).strip(),
                "series": str(
                    row.series
                ).strip(),
                "source_timestamp":
                    timestamp.to_pydatetime(),
            }
        )

    return records


def load_fact_records(
    connection: Connection,
    fact_records: list[dict[str, Any]],
) -> int:
    """
    Insert or update fact_oil_price records.
    """

    if not fact_records:
        logger.warning(
            "No fact records available to load"
        )
        return 0

    upsert_sql = text(
        """
        INSERT INTO fact_oil_price
        (
            time_key,
            product_key,
            price_usd,
            unit,
            source,
            series,
            source_timestamp
        )
        VALUES
        (
            :time_key,
            :product_key,
            :price_usd,
            :unit,
            :source,
            :series,
            :source_timestamp
        )
        ON CONFLICT
        (
            time_key,
            product_key,
            source,
            series
        )
        DO UPDATE SET
            price_usd =
                EXCLUDED.price_usd,
            unit =
                EXCLUDED.unit,
            source_timestamp =
                EXCLUDED.source_timestamp,
            ingestion_time =
                CURRENT_TIMESTAMP;
        """
    )

    connection.execute(
        upsert_sql,
        fact_records,
    )

    logger.success(
        "fact_oil_price processed: {} rows",
        len(fact_records),
    )

    return len(fact_records)


def load_facts() -> int:
    logger.info(
        "Starting oil-price fact loading"
    )

    dataframe = read_oil_price_parquet()

    engine = get_engine()

    with engine.begin() as connection:
        time_mapping = get_time_mapping(
            connection,
            dataframe,
        )

        product_mapping = get_product_mapping(
            connection,
            dataframe,
        )

        fact_records = build_fact_records(
            dataframe,
            time_mapping,
            product_mapping,
        )

        loaded_rows = load_fact_records(
            connection,
            fact_records,
        )

    logger.success(
        "Oil-price fact loading completed"
    )

    return loaded_rows


def main() -> None:
    load_facts()


if __name__ == "__main__":
    main()