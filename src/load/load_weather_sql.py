from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from src.config.config import DB
from src.utils.logger import logger

PARQUET_FILE = Path("data/processed/weather/weather_clean.parquet")

def get_engine():

    connection_string = (
        f"postgresql://"
        f"{DB['user']}:"
        f"{DB['password']}@"
        f"{DB['host']}:"
        f"{DB['port']}/"
        f"{DB['database']}"
    )

    return create_engine(connection_string)

def load_weather():

    logger.info(
        "Reading silver parquet"
    )

    df = pd.read_parquet(
        PARQUET_FILE
    )

    engine = get_engine()

    logger.info(
        "Loading weather table"
    )

    df.to_sql(
        name="weather_fact",
        con=engine,
        if_exists="append",
        index=False
    )

    logger.success(
        "Weather data loaded into PostgreSQL"
    )


if __name__ == "__main__":
    load_weather()