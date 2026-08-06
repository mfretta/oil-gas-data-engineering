import os

from dotenv import load_dotenv


load_dotenv(override=True)


# ==========================
# Database
# ==========================

DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


# ==========================
# APIs
# ==========================

EIA_API_KEY = os.getenv("EIA_API_KEY")

OPEN_METEO_URL = os.getenv(
    "OPEN_METEO_URL",
    "https://api.open-meteo.com/v1/forecast",
)

REQUEST_TIMEOUT = 30


# ==========================
# Paths
# ==========================

RAW_WEATHER_FOLDER = "data/raw/weather"

from pathlib import Path


RAW_RIG_COUNT_FOLDER = Path(
    "data/raw/rig_count"
)

PROCESSED_RIG_COUNT_FOLDER = Path(
    "data/processed/rig_count"
)

RIG_COUNT_PARQUET_FILE = (
    PROCESSED_RIG_COUNT_FOLDER
    / "rig_count.parquet"
)

from pathlib import Path


from pathlib import Path


# ==========================
# Weather API
# ==========================

OPEN_METEO_URL = os.getenv(
    "OPEN_METEO_URL",
    "https://api.open-meteo.com/v1/forecast",
)

OPEN_METEO_MARINE_URL = os.getenv(
    "OPEN_METEO_MARINE_URL",
    "https://marine-api.open-meteo.com/v1/marine",
)

REQUEST_TIMEOUT = int(
    os.getenv("REQUEST_TIMEOUT", "30")
)

WEATHER_FORECAST_DAYS = int(
    os.getenv("WEATHER_FORECAST_DAYS", "7")
)


# ==========================
# Weather paths
# ==========================

ASSET_REGISTRY_FILE = Path(
    "data/reference/offshore_assets.csv"
)

RAW_ATMOSPHERIC_FOLDER = Path(
    "data/raw/weather/atmospheric"
)

RAW_MARINE_FOLDER = Path(
    "data/raw/weather/marine"
)

PROCESSED_WEATHER_FOLDER = Path(
    "data/processed/weather"
)

ATMOSPHERIC_PARQUET_FILE = (
    PROCESSED_WEATHER_FOLDER
    / "atmospheric_forecast.parquet"
)

MARINE_PARQUET_FILE = (
    PROCESSED_WEATHER_FOLDER
    / "marine_forecast.parquet"
)