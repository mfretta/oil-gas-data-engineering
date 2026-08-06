import json
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.config.config import (
    ATMOSPHERIC_PARQUET_FILE,
    RAW_ATMOSPHERIC_FOLDER,
)


REQUIRED_HOURLY_FIELDS = {
    "time",
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "visibility",
    "weather_code",
}


class AtmosphericForecastTransformer:
    """
    Transform the latest multi-asset atmospheric Bronze JSON
    into a standardized Silver Parquet dataset.
    """

    def get_latest_bronze_file(self) -> Path:
        files = [
            file
            for file in RAW_ATMOSPHERIC_FOLDER.rglob("*.json")
            if file.is_file() and file.stat().st_size > 0
        ]

        if not files:
            raise FileNotFoundError(
                "No atmospheric Bronze JSON files found under "
                f"{RAW_ATMOSPHERIC_FOLDER.resolve()}."
            )

        latest_file = max(
            files,
            key=lambda file: file.stat().st_mtime,
        )

        logger.info(
            "Selected atmospheric Bronze file: {}",
            latest_file,
        )

        return latest_file

    @staticmethod
    def load_json(file_path: Path) -> dict[str, Any]:
        logger.info(
            "Loading atmospheric Bronze JSON: {}",
            file_path,
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        if payload.get("dataset") != "atmospheric_forecast":
            raise ValueError(
                "Unexpected dataset in atmospheric Bronze file: "
                f"{payload.get('dataset')}"
            )

        if not payload.get("assets"):
            raise ValueError(
                "Atmospheric Bronze file contains no assets."
            )

        return payload

    @staticmethod
    def validate_hourly_data(
        hourly: dict[str, Any],
        asset_id: str,
    ) -> None:
        missing = REQUIRED_HOURLY_FIELDS - set(hourly)

        if missing:
            raise ValueError(
                f"Atmospheric response for {asset_id} is missing: "
                + ", ".join(sorted(missing))
            )

        expected_length = len(hourly["time"])

        for field in REQUIRED_HOURLY_FIELDS:
            field_length = len(hourly[field])

            if field_length != expected_length:
                raise ValueError(
                    f"Atmospheric field '{field}' for {asset_id} "
                    f"contains {field_length} values; expected "
                    f"{expected_length}."
                )

    def transform(
        self,
        payload: dict[str, Any],
        source_file: Path,
    ) -> pd.DataFrame:
        logger.info(
            "Transforming atmospheric forecasts"
        )

        forecast_reference_time = pd.to_datetime(
            payload["ingestion_time"],
            utc=True,
            errors="coerce",
        )

        if pd.isna(forecast_reference_time):
            raise ValueError(
                "Invalid atmospheric ingestion_time."
            )

        forecast_reference_time = (
            forecast_reference_time.tz_localize(None)
        )

        records: list[dict[str, Any]] = []

        for asset_entry in payload["assets"]:
            asset = asset_entry["asset"]
            api_response = asset_entry["api_response"]
            hourly = api_response["hourly"]

            asset_id = str(asset["asset_id"]).strip()

            self.validate_hourly_data(
                hourly=hourly,
                asset_id=asset_id,
            )

            number_of_hours = len(hourly["time"])

            for index in range(number_of_hours):
                valid_time = pd.to_datetime(
                    hourly["time"][index],
                    errors="coerce",
                    utc=True,
                )

                if pd.isna(valid_time):
                    continue

                valid_time = valid_time.tz_localize(None)

                forecast_horizon_hours = int(
                    (
                        valid_time
                        - forecast_reference_time
                    ).total_seconds()
                    // 3600
                )

                records.append(
                    {
                        "forecast_reference_time":
                            forecast_reference_time,

                        "forecast_valid_time":
                            valid_time,

                        "forecast_horizon_hours":
                            max(
                                forecast_horizon_hours,
                                0,
                            ),

                        "asset_id":
                            asset_id,

                        "location_id":
                            str(
                                asset["location_id"]
                            ).strip(),

                        "latitude":
                            float(asset["latitude"]),

                        "longitude":
                            float(asset["longitude"]),

                        "temperature_c":
                            hourly[
                                "temperature_2m"
                            ][index],

                        "relative_humidity_pct":
                            hourly[
                                "relative_humidity_2m"
                            ][index],

                        "precipitation_mm":
                            hourly[
                                "precipitation"
                            ][index],

                        "pressure_hpa":
                            hourly[
                                "pressure_msl"
                            ][index],

                        "wind_speed_kmh":
                            hourly[
                                "wind_speed_10m"
                            ][index],

                        "wind_direction_deg":
                            hourly[
                                "wind_direction_10m"
                            ][index],

                        "wind_gust_kmh":
                            hourly[
                                "wind_gusts_10m"
                            ][index],

                        "visibility_m":
                            hourly[
                                "visibility"
                            ][index],

                        "weather_code":
                            hourly[
                                "weather_code"
                            ][index],

                        "source":
                            "Open-Meteo",

                        "source_file":
                            source_file.name,
                    }
                )

        dataframe = pd.DataFrame(records)

        if dataframe.empty:
            raise ValueError(
                "Atmospheric transformation produced no rows."
            )

        numeric_columns = [
            "forecast_horizon_hours",
            "latitude",
            "longitude",
            "temperature_c",
            "relative_humidity_pct",
            "precipitation_mm",
            "pressure_hpa",
            "wind_speed_kmh",
            "wind_direction_deg",
            "wind_gust_kmh",
            "visibility_m",
            "weather_code",
        ]

        for column in numeric_columns:
            dataframe[column] = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )

        dataframe = dataframe.dropna(
            subset=[
                "forecast_reference_time",
                "forecast_valid_time",
                "asset_id",
                "forecast_horizon_hours",
            ]
        )

        dataframe = dataframe[
            dataframe["forecast_horizon_hours"] >= 0
        ]

        dataframe = dataframe.drop_duplicates(
            subset=[
                "asset_id",
                "forecast_reference_time",
                "forecast_valid_time",
                "source",
            ],
            keep="last",
        )

        dataframe = dataframe.sort_values(
            by=[
                "asset_id",
                "forecast_valid_time",
            ]
        ).reset_index(drop=True)

        logger.success(
            "Atmospheric transformation completed: {} rows",
            len(dataframe),
        )

        return dataframe

    @staticmethod
    def save_parquet(
        dataframe: pd.DataFrame,
    ) -> Path:
        ATMOSPHERIC_PARQUET_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        dataframe.to_parquet(
            ATMOSPHERIC_PARQUET_FILE,
            index=False,
        )

        logger.success(
            "Atmospheric Silver Parquet saved: {}",
            ATMOSPHERIC_PARQUET_FILE,
        )

        return ATMOSPHERIC_PARQUET_FILE

    def execute(self) -> Path:
        bronze_file = self.get_latest_bronze_file()

        payload = self.load_json(
            bronze_file
        )

        dataframe = self.transform(
            payload=payload,
            source_file=bronze_file,
        )

        output_file = self.save_parquet(
            dataframe
        )

        print("\nAtmospheric Silver columns:")
        print(dataframe.columns.tolist())

        print("\nAtmospheric preview:")
        print(
            dataframe.head(10).to_string(
                index=False
            )
        )

        return output_file


def main() -> None:
    transformer = AtmosphericForecastTransformer()
    transformer.execute()


if __name__ == "__main__":
    main()