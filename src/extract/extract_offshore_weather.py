from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.api.marine_api import MarineAPI
from src.api.weather_api import WeatherAPI
from src.config.config import (
    ASSET_REGISTRY_FILE,
    RAW_ATMOSPHERIC_FOLDER,
    RAW_MARINE_FOLDER,
)
from src.utils.bronze_writer import (
    save_bronze_json,
)


REQUIRED_ASSET_COLUMNS = {
    "asset_id",
    "asset_name",
    "asset_type",
    "location_id",
    "latitude",
    "longitude",
}


class OffshoreWeatherExtractor:
    """
    Retrieve atmospheric and marine forecasts for all
    active offshore portfolio assets.
    """

    def __init__(self) -> None:
        self.weather_api = WeatherAPI()
        self.marine_api = MarineAPI()

    @staticmethod
    def read_asset_registry() -> pd.DataFrame:
        if not ASSET_REGISTRY_FILE.exists():
            raise FileNotFoundError(
                "Asset registry not found: "
                f"{ASSET_REGISTRY_FILE.resolve()}"
            )

        dataframe = pd.read_csv(
            ASSET_REGISTRY_FILE
        )

        missing_columns = (
            REQUIRED_ASSET_COLUMNS
            - set(dataframe.columns)
        )

        if missing_columns:
            raise ValueError(
                "Asset registry is missing columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        if dataframe.empty:
            raise ValueError(
                "Asset registry contains no records."
            )

        dataframe["latitude"] = pd.to_numeric(
            dataframe["latitude"],
            errors="coerce",
        )

        dataframe["longitude"] = pd.to_numeric(
            dataframe["longitude"],
            errors="coerce",
        )

        dataframe = dataframe.dropna(
            subset=[
                "asset_id",
                "location_id",
                "latitude",
                "longitude",
            ]
        )

        dataframe = dataframe[
            dataframe["latitude"].between(
                -90,
                90,
            )
        ]

        dataframe = dataframe[
            dataframe["longitude"].between(
                -180,
                180,
            )
        ]

        dataframe = dataframe.drop_duplicates(
            subset=["asset_id"],
            keep="last",
        )

        if dataframe.empty:
            raise ValueError(
                "No valid assets remain after validation."
            )

        logger.info(
            "Asset registry loaded: {} assets",
            len(dataframe),
        )

        return dataframe.reset_index(
            drop=True
        )

    @staticmethod
    def build_asset_metadata(
        dataframe: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        metadata_columns = [
            "asset_id",
            "asset_name",
            "asset_type",
            "location_id",
            "latitude",
            "longitude",
        ]

        optional_columns = [
            "operator_name",
            "location_name",
            "country",
        ]

        selected_columns = (
            metadata_columns
            + [
                column
                for column in optional_columns
                if column in dataframe.columns
            ]
        )

        return dataframe[
            selected_columns
        ].to_dict("records")

    @staticmethod
    def attach_assets_to_responses(
        responses: list[dict[str, Any]],
        assets: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if len(responses) != len(assets):
            raise ValueError(
                "Cannot attach asset metadata because "
                "response and asset counts differ."
            )

        enriched_responses = []

        for index, response in enumerate(
            responses
        ):
            enriched_responses.append(
                {
                    "request_index": index,
                    "asset": assets[index],
                    "api_response": response,
                }
            )

        return enriched_responses

    def extract_atmospheric(
        self,
        assets_df: pd.DataFrame,
        ingestion_time: datetime,
    ) -> Path:
        latitudes = (
            assets_df["latitude"]
            .astype(float)
            .tolist()
        )

        longitudes = (
            assets_df["longitude"]
            .astype(float)
            .tolist()
        )

        assets = self.build_asset_metadata(
            assets_df
        )

        responses = (
            self.weather_api
            .get_hourly_forecast(
                latitudes=latitudes,
                longitudes=longitudes,
            )
        )

        enriched = (
            self.attach_assets_to_responses(
                responses,
                assets,
            )
        )

        payload = {
            "dataset": "atmospheric_forecast",
            "source": "Open-Meteo",
            "ingestion_time":
                ingestion_time.isoformat(),
            "asset_count": len(assets),
            "assets": enriched,
        }

        return save_bronze_json(
            payload=payload,
            root_folder=
                RAW_ATMOSPHERIC_FOLDER,
            filename_prefix=
                "atmospheric_forecast",
            ingestion_time=ingestion_time,
        )

    def extract_marine(
        self,
        assets_df: pd.DataFrame,
        ingestion_time: datetime,
    ) -> Path:
        latitudes = (
            assets_df["latitude"]
            .astype(float)
            .tolist()
        )

        longitudes = (
            assets_df["longitude"]
            .astype(float)
            .tolist()
        )

        assets = self.build_asset_metadata(
            assets_df
        )

        responses = (
            self.marine_api
            .get_hourly_forecast(
                latitudes=latitudes,
                longitudes=longitudes,
            )
        )

        enriched = (
            self.attach_assets_to_responses(
                responses,
                assets,
            )
        )

        payload = {
            "dataset": "marine_forecast",
            "source": "Open-Meteo Marine",
            "ingestion_time":
                ingestion_time.isoformat(),
            "asset_count": len(assets),
            "assets": enriched,
        }

        return save_bronze_json(
            payload=payload,
            root_folder=
                RAW_MARINE_FOLDER,
            filename_prefix=
                "marine_forecast",
            ingestion_time=ingestion_time,
        )

    def execute(self) -> dict[str, Path]:
        logger.info(
            "Starting multi-asset offshore weather extraction"
        )

        ingestion_time = datetime.now(
            timezone.utc
        )

        assets_df = self.read_asset_registry()

        atmospheric_file = (
            self.extract_atmospheric(
                assets_df,
                ingestion_time,
            )
        )

        marine_file = self.extract_marine(
            assets_df,
            ingestion_time,
        )

        logger.success(
            "Offshore atmospheric and marine extraction "
            "completed"
        )

        return {
            "atmospheric":
                atmospheric_file,
            "marine":
                marine_file,
        }


def main() -> None:
    extractor = OffshoreWeatherExtractor()

    files = extractor.execute()

    print("\nCreated Bronze files:")

    for dataset, filepath in files.items():
        print(
            f"{dataset}: {filepath}"
        )


if __name__ == "__main__":
    main()