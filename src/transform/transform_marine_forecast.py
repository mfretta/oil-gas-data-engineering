import json
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.config.config import (
    MARINE_PARQUET_FILE,
    RAW_MARINE_FOLDER,
)


REQUIRED_MARINE_FIELDS = {
    "time",
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
}


class MarineForecastTransformer:
    """
    Transform the latest multi-asset marine Bronze JSON
    into a standardized Silver Parquet dataset.
    """

    def get_latest_bronze_file(self) -> Path:
        files = [
            file
            for file in RAW_MARINE_FOLDER.rglob("*.json")
            if file.is_file() and file.stat().st_size > 0
        ]

        if not files:
            raise FileNotFoundError(
                "No marine Bronze JSON files found under "
                f"{RAW_MARINE_FOLDER.resolve()}."
            )

        latest_file = max(
            files,
            key=lambda file: file.stat().st_mtime,
        )

        logger.info(
            "Selected marine Bronze file: {}",
            latest_file,
        )

        return latest_file

    @staticmethod
    def load_json(file_path: Path) -> dict[str, Any]:
        logger.info(
            "Loading marine Bronze JSON: {}",
            file_path,
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        if payload.get("dataset") != "marine_forecast":
            raise ValueError(
                "Unexpected dataset in marine Bronze file: "
                f"{payload.get('dataset')}"
            )

        if not payload.get("assets"):
            raise ValueError(
                "Marine Bronze file contains no assets."
            )

        return payload

    @staticmethod
    def validate_hourly_data(
        hourly: dict[str, Any],
        asset_id: str,
    ) -> None:
        missing = REQUIRED_MARINE_FIELDS - set(hourly)

        if missing:
            raise ValueError(
                f"Marine response for {asset_id} is missing: "
                + ", ".join(sorted(missing))
            )

        expected_length = len(hourly["time"])

        for field in REQUIRED_MARINE_FIELDS:
            field_length = len(hourly[field])

            if field_length != expected_length:
                raise ValueError(
                    f"Marine field '{field}' for {asset_id} "
                    f"contains {field_length} values; expected "
                    f"{expected_length}."
                )

    def transform(
        self,
        payload: dict[str, Any],
        source_file: Path,
    ) -> pd.DataFrame:
        logger.info(
            "Transforming marine forecasts"
        )

        forecast_reference_time = pd.to_datetime(
            payload["ingestion_time"],
            errors="coerce",
            utc=True,
        )

        if pd.isna(forecast_reference_time):
            raise ValueError(
                "Invalid marine ingestion_time."
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

                        "wave_height_m":
                            hourly[
                                "wave_height"
                            ][index],

                        "wave_direction_deg":
                            hourly[
                                "wave_direction"
                            ][index],

                        "wave_period_s":
                            hourly[
                                "wave_period"
                            ][index],

                        "wind_wave_height_m":
                            hourly[
                                "wind_wave_height"
                            ][index],

                        "swell_wave_height_m":
                            hourly[
                                "swell_wave_height"
                            ][index],

                        "swell_wave_direction_deg":
                            hourly[
                                "swell_wave_direction"
                            ][index],

                        "swell_wave_period_s":
                            hourly[
                                "swell_wave_period"
                            ][index],

                        "sea_surface_temperature_c":
                            hourly[
                                "sea_surface_temperature"
                            ][index],

                        "ocean_current_velocity_kmh":
                            hourly[
                                "ocean_current_velocity"
                            ][index],

                        "ocean_current_direction_deg":
                            hourly[
                                "ocean_current_direction"
                            ][index],

                        "source":
                            "Open-Meteo Marine",

                        "source_file":
                            source_file.name,
                    }
                )

        dataframe = pd.DataFrame(records)

        if dataframe.empty:
            raise ValueError(
                "Marine transformation produced no rows."
            )

        numeric_columns = [
            "forecast_horizon_hours",
            "latitude",
            "longitude",
            "wave_height_m",
            "wave_direction_deg",
            "wave_period_s",
            "wind_wave_height_m",
            "swell_wave_height_m",
            "swell_wave_direction_deg",
            "swell_wave_period_s",
            "sea_surface_temperature_c",
            "ocean_current_velocity_kmh",
            "ocean_current_direction_deg",
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

        non_negative_columns = [
            "wave_height_m",
            "wave_period_s",
            "wind_wave_height_m",
            "swell_wave_height_m",
            "swell_wave_period_s",
            "ocean_current_velocity_kmh",
        ]

        for column in non_negative_columns:
            dataframe.loc[
                dataframe[column] < 0,
                column,
            ] = pd.NA

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
            "Marine transformation completed: {} rows",
            len(dataframe),
        )

        return dataframe

    @staticmethod
    def save_parquet(
        dataframe: pd.DataFrame,
    ) -> Path:
        MARINE_PARQUET_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        dataframe.to_parquet(
            MARINE_PARQUET_FILE,
            index=False,
        )

        logger.success(
            "Marine Silver Parquet saved: {}",
            MARINE_PARQUET_FILE,
        )

        return MARINE_PARQUET_FILE

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

        print("\nMarine Silver columns:")
        print(dataframe.columns.tolist())

        print("\nMarine preview:")
        print(
            dataframe.head(10).to_string(
                index=False
            )
        )

        return output_file


def main() -> None:
    transformer = MarineForecastTransformer()
    transformer.execute()


if __name__ == "__main__":
    main()