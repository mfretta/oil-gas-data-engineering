from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


ASSET_FILE = Path(
    "data/reference/offshore_assets.csv"
)


REQUIRED_COLUMNS = {
    "asset_id",
    "asset_name",
    "asset_type",
    "operator_name",
    "location_id",
    "location_name",
    "country",
    "latitude",
    "longitude",
    "max_wind_kmh",
    "max_gust_kmh",
    "max_wave_height_m",
    "minimum_visibility_m",
}


def read_asset_registry() -> pd.DataFrame:
    if not ASSET_FILE.exists():
        raise FileNotFoundError(
            f"Asset registry not found: "
            f"{ASSET_FILE.resolve()}"
        )

    dataframe = pd.read_csv(ASSET_FILE)

    missing = REQUIRED_COLUMNS - set(
        dataframe.columns
    )

    if missing:
        raise ValueError(
            "Asset registry is missing columns: "
            + ", ".join(sorted(missing))
        )

    if dataframe.empty:
        raise ValueError(
            "Asset registry contains no records."
        )

    return dataframe


def load_locations(
    dataframe: pd.DataFrame,
) -> None:
    statement = text(
        """
        INSERT INTO dim_location
        (
            location_id,
            location_name,
            country,
            latitude,
            longitude
        )
        VALUES
        (
            :location_id,
            :location_name,
            :country,
            :latitude,
            :longitude
        )
        ON CONFLICT (location_id)
        DO UPDATE SET
            location_name =
                EXCLUDED.location_name,
            country =
                EXCLUDED.country,
            latitude =
                EXCLUDED.latitude,
            longitude =
                EXCLUDED.longitude;
        """
    )

    records = (
        dataframe[
            [
                "location_id",
                "location_name",
                "country",
                "latitude",
                "longitude",
            ]
        ]
        .drop_duplicates()
        .to_dict("records")
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            statement,
            records,
        )

    logger.success(
        "Weather locations processed: {}",
        len(records),
    )


def load_assets(
    dataframe: pd.DataFrame,
) -> None:
    statement = text(
        """
        INSERT INTO dim_asset
        (
            asset_id,
            asset_name,
            asset_type,
            operator_name,
            location_key,
            is_active,
            max_wind_kmh,
            max_gust_kmh,
            max_wave_height_m,
            minimum_visibility_m
        )
        SELECT
            :asset_id,
            :asset_name,
            :asset_type,
            :operator_name,
            location_key,
            TRUE,
            :max_wind_kmh,
            :max_gust_kmh,
            :max_wave_height_m,
            :minimum_visibility_m
        FROM dim_location
        WHERE location_id = :location_id

        ON CONFLICT (asset_id)
        DO UPDATE SET
            asset_name =
                EXCLUDED.asset_name,
            asset_type =
                EXCLUDED.asset_type,
            operator_name =
                EXCLUDED.operator_name,
            location_key =
                EXCLUDED.location_key,
            is_active =
                EXCLUDED.is_active,
            max_wind_kmh =
                EXCLUDED.max_wind_kmh,
            max_gust_kmh =
                EXCLUDED.max_gust_kmh,
            max_wave_height_m =
                EXCLUDED.max_wave_height_m,
            minimum_visibility_m =
                EXCLUDED.minimum_visibility_m,
            updated_at =
                CURRENT_TIMESTAMP;
        """
    )

    records = dataframe.to_dict("records")

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            statement,
            records,
        )

    logger.success(
        "Weather assets processed: {}",
        len(records),
    )


def load_weather_dimensions() -> None:
    logger.info(
        "Starting weather dimension loading"
    )

    dataframe = read_asset_registry()

    load_locations(dataframe)
    load_assets(dataframe)

    logger.success(
        "Weather dimensions loaded successfully"
    )


def main() -> None:
    load_weather_dimensions()


if __name__ == "__main__":
    main()