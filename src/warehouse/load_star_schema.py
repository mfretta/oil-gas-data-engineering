import pandas as pd
from sqlalchemy import create_engine, text

from src.config.config import DB
from src.utils.logger import logger


PARQUET_FILE = "data/processed/weather/weather_clean.parquet"


def get_engine():
    connection = (
        f"postgresql://"
        f"{DB['user']}:"
        f"{DB['password']}@"
        f"{DB['host']}:"
        f"{DB['port']}/"
        f"{DB['database']}"
    )

    return create_engine(connection)


def load_location(df, engine):

    location = df[
        [
            "location_id",
            "latitude",
            "longitude"
        ]
    ].drop_duplicates()

    location["location_name"] = location["location_id"]
    location["country"] = "UAE"

    location.to_sql(
        "dim_location",
        engine,
        if_exists="append",
        index=False
    )

    logger.success("dim_location loaded")


def load_time(df, engine):

    time_df = pd.DataFrame()

    time_df["timestamp"] = df["timestamp"]
    time_df["date"] = df["timestamp"].dt.date
    time_df["hour"] = df["timestamp"].dt.hour
    time_df["month"] = df["timestamp"].dt.month

    def get_season(month):
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Autumn"

    time_df["season"] = time_df["month"].apply(get_season)

    time_df = time_df.drop_duplicates()

    time_df.to_sql(
        "dim_time",
        engine,
        if_exists="append",
        index=False
    )

    logger.success("dim_time loaded")


def load_fact_weather(df, engine):

    logger.info("Loading fact_weather")

    dim_location = pd.read_sql(
        "SELECT location_key, location_id FROM dim_location",
        engine
    )

    dim_time = pd.read_sql(
        "SELECT time_key, timestamp FROM dim_time",
        engine
    )

    fact = df.merge(
        dim_location,
        on="location_id",
        how="left"
    )

    fact = fact.merge(
        dim_time,
        on="timestamp",
        how="left"
    )

    fact = fact[
        [
            "time_key",
            "location_key",
            "temperature_c",
            "humidity",
            "wind_kmh",
            "ingestion_time"
        ]
    ]

    fact.to_sql(
        "fact_weather",
        engine,
        if_exists="append",
        index=False
    )

    logger.success("fact_weather loaded")


def main():

    logger.info("Reading parquet")

    df = pd.read_parquet(PARQUET_FILE)

    engine = get_engine()

    # Development only: clear warehouse tables
    with engine.begin() as conn:
        conn.execute(text("""
            TRUNCATE TABLE
                fact_weather,
                dim_time,
                dim_location
            RESTART IDENTITY CASCADE;
        """))

    load_location(df, engine)
    load_time(df, engine)
    load_fact_weather(df, engine)

    logger.success("Warehouse successfully loaded.")


if __name__ == "__main__":
    main()