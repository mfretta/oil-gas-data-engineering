import json

from pathlib import Path

from datetime import datetime, UTC

from src.api.weather_api import WeatherAPI

from src.config.config import RAW_WEATHER_FOLDER

from src.utils.logger import logger


def save_json(data):

    Path(RAW_WEATHER_FOLDER).mkdir(
        parents=True,
        exist_ok=True
    )

    filename = datetime.now(UTC).strftime(
        "%Y%m%d_%H%M%S_weather.json"
    )

    filepath = Path(RAW_WEATHER_FOLDER) / filename

    with open(filepath, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            indent=4
        )

    logger.success(f"Saved {filepath}")


def extract_weather():

    api = WeatherAPI()

    data = api.get_weather(

        latitude=25.2048,

        longitude=55.2708

    )

    save_json(data)


if __name__ == "__main__":

    extract_weather()