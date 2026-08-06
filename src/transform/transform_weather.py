import json
from pathlib import Path
from datetime import datetime, UTC

import pandas as pd

from src.utils.logger import logger
from src.config.config import RAW_WEATHER_FOLDER


PROCESSED_FOLDER = Path("data/processed/weather")


def read_raw_weather():
    """
    Read JSON files from Bronze layer
    """

    files = list(Path(RAW_WEATHER_FOLDER).glob("*.json"))

    if not files:
        raise FileNotFoundError(
            "No weather JSON files found"
        )

    latest_file = max(
        files,
        key=lambda x: x.stat().st_mtime
    )

    logger.info(
        f"Reading file {latest_file}"
    )

    with open(latest_file, "r") as f:
        data = json.load(f)

    return data


def flatten_weather(data):
    """
    Flatten Open-Meteo hourly weather response
    """

    hourly = data.get("hourly", {})

    timestamps = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    humidity = hourly.get("relative_humidity_2m", [])
    wind = hourly.get("wind_speed_10m", [])

    records = []

    for i, timestamp in enumerate(timestamps):

        records.append({

            "latitude": data.get("latitude"),

            "longitude": data.get("longitude"),

            "timezone": data.get("timezone"),

            "timestamp": timestamp,

            "temperature_c":
                temperatures[i]
                if i < len(temperatures)
                else None,

            "humidity":
                humidity[i]
                if i < len(humidity)
                else None,

            "wind_kmh":
                wind[i]
                if i < len(wind)
                else None
        })

    return records


def clean_weather(df):

    # timestamp conversion
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # remove invalid rows
    df.dropna(
        subset=["timestamp"],
        inplace=True
    )

    # fill missing numerical values
    numeric_columns = [
        "temperature_c",
        "humidity",
        "wind_kmh",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df[numeric_columns] = (
        df[numeric_columns]
        .fillna(0)
    )
     # Metadata
    df["ingestion_time"] = datetime.now(UTC)

    # Future offshore assets
    df["location_id"] = "DUBAI"
    return df


def save_parquet(df):

    PROCESSED_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    output = (
        PROCESSED_FOLDER /
        "weather_clean.parquet"
    )

    df.to_parquet(
        output,
        engine="pyarrow",
        index=False
    )

    logger.success(
        f"Saved {output}"
    )


def main():

    raw = read_raw_weather()

    weather = flatten_weather(raw)

    df = pd.DataFrame(
        weather
    )

    df = clean_weather(df)

    # Data Quality Checks
    assert not df.empty, "Weather dataframe is empty"

    assert df["temperature_c"].notna().all(), \
        "Missing temperature values"

    assert df["wind_kmh"].notna().all(), \
        "Missing wind values"

    save_parquet(df)


if __name__ == "__main__":
    main()