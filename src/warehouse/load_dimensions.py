from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy import text

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
    if not PARQUET_FILE.exists():
        raise FileNotFoundError(
            f"Parquet file not found: "
            f"{PARQUET_FILE.resolve()}"
        )

    logger.info(
        "Reading Silver Parquet: {}",
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
            "Oil-price Parquet is empty."
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

    df = df.dropna(
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

    df = df[df["price_usd"] >= 0]

    df = df.drop_duplicates(
        subset=[
            "timestamp",
            "series",
        ],
        keep="last",
    )

    if df.empty:
        raise ValueError(
            "No valid rows remain after validation."
        )

    logger.success(
        "Silver Parquet validated: {} rows",
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


def identify_commodity_type(
    product_name: str,
) -> str:
    product_upper = product_name.upper()

    if (
        "DIESEL" in product_upper
        or "GASOLINE" in product_upper
        or "JET FUEL" in product_upper
    ):
        return "REFINED_PRODUCT"

    if (
        "BRENT" in product_upper
        or "WTI" in product_upper
        or "CRUDE" in product_upper
    ):
        return "CRUDE_OIL"

    if "NATURAL GAS" in product_upper:
        return "NATURAL_GAS"

    return "ENERGY_COMMODITY"


def load_dim_time(
    df: pd.DataFrame,
) -> int:
    timestamps = (
        df["timestamp"]
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
        for timestamp in timestamps:
            timestamp = pd.Timestamp(timestamp)

            connection.execute(
                insert_sql,
                {
                    "timestamp":
                        timestamp.to_pydatetime(),
                    "date":
                        timestamp.date(),
                    "hour":
                        int(timestamp.hour),
                    "month":
                        int(timestamp.month),
                    "season":
                        get_season(
                            int(timestamp.month)
                        ),
                },
            )

    logger.success(
        "dim_time processed: {} timestamps",
        len(timestamps),
    )

    return len(timestamps)


def load_dim_energy_product(
    df: pd.DataFrame,
) -> int:
    products = (
        df[
            [
                "product_code",
                "product",
                "unit",
            ]
        ]
        .drop_duplicates()
        .to_dict("records")
    )

    upsert_sql = text(
        """
        INSERT INTO dim_energy_product
        (
            product_code,
            product_name,
            commodity_type,
            default_unit
        )
        VALUES
        (
            :product_code,
            :product_name,
            :commodity_type,
            :default_unit
        )
        ON CONFLICT (product_code)
        DO UPDATE SET
            product_name =
                EXCLUDED.product_name,
            commodity_type =
                EXCLUDED.commodity_type,
            default_unit =
                EXCLUDED.default_unit,
            updated_at =
                CURRENT_TIMESTAMP;
        """
    )

    engine = get_engine()

    with engine.begin() as connection:
        for product in products:
            product_code = str(
                product["product_code"]
            ).strip().upper()

            product_name = str(
                product["product"]
            ).strip()

            default_unit = str(
                product["unit"]
            ).strip()

            connection.execute(
                upsert_sql,
                {
                    "product_code":
                        product_code,
                    "product_name":
                        product_name,
                    "commodity_type":
                        identify_commodity_type(
                            product_name
                        ),
                    "default_unit":
                        default_unit,
                },
            )

    logger.success(
        "dim_energy_product processed: {} products",
        len(products),
    )

    return len(products)


def load_dimensions() -> None:
    logger.info(
        "Starting oil-price dimension loading"
    )

    df = read_oil_price_parquet()

    load_dim_time(df)

    load_dim_energy_product(df)

    logger.success(
        "Oil-price dimensions loaded successfully"
    )


def main() -> None:
    load_dimensions()


if __name__ == "__main__":
    main()