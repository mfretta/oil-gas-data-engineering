from typing import Any

import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.config import (
    OPEN_METEO_MARINE_URL,
    REQUEST_TIMEOUT,
    WEATHER_FORECAST_DAYS,
)


MARINE_HOURLY_VARIABLES = [
    "wave_height",
    "wave_direction",
    "wave_period",
    "wind_wave_height",
    "swell_wave_height",
    "swell_wave_direction",
    "swell_wave_period",
    "sea_surface_temperature",
    "ocean_current_velocity",
    "ocean_current_direction",
]


class MarineAPI:
    """
    Open-Meteo marine forecast API client.
    """

    def __init__(self) -> None:
        self.base_url = OPEN_METEO_MARINE_URL
        self.session = self._create_session()

    @staticmethod
    def _create_session() -> requests.Session:
        retry_strategy = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1,
            status_forcelist=[
                429,
                500,
                502,
                503,
                504,
            ],
            allowed_methods=["GET"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy
        )

        session = requests.Session()

        session.mount(
            "https://",
            adapter,
        )

        session.mount(
            "http://",
            adapter,
        )

        session.headers.update(
            {
                "User-Agent":
                    "oil-gas-data-engineering/1.0"
            }
        )

        return session

    def get_hourly_forecast(
        self,
        latitudes: list[float],
        longitudes: list[float],
    ) -> list[dict[str, Any]]:
        """
        Retrieve hourly marine forecasts for multiple
        offshore coordinates.
        """

        if not latitudes or not longitudes:
            raise ValueError(
                "Latitude and longitude lists cannot be empty."
            )

        if len(latitudes) != len(longitudes):
            raise ValueError(
                "Latitude and longitude lists must have "
                "the same length."
            )

        params = {
            "latitude": ",".join(
                str(value)
                for value in latitudes
            ),
            "longitude": ",".join(
                str(value)
                for value in longitudes
            ),
            "hourly": ",".join(
                MARINE_HOURLY_VARIABLES
            ),
            "forecast_days":
                WEATHER_FORECAST_DAYS,
            "timezone": "UTC",
        }

        logger.info(
            "Calling marine API for {} assets",
            len(latitudes),
        )

        response = self.session.get(
            self.base_url,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

        if isinstance(payload, dict):
            payload = [payload]

        if not isinstance(payload, list):
            raise ValueError(
                "Unexpected marine API response type: "
                f"{type(payload).__name__}"
            )

        if len(payload) != len(latitudes):
            raise ValueError(
                "Marine response count does not match "
                f"asset count: {len(payload)} responses for "
                f"{len(latitudes)} assets."
            )

        for index, result in enumerate(payload):
            if "hourly" not in result:
                raise ValueError(
                    "Marine response is missing 'hourly' "
                    f"for response index {index}."
                )

            if "time" not in result["hourly"]:
                raise ValueError(
                    "Marine response hourly object is "
                    f"missing 'time' at index {index}."
                )

        logger.success(
            "Marine forecast received for {} assets",
            len(payload),
        )

        return payload