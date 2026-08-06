from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config.database import get_engine
from src.config.config import (
    ATMOSPHERIC_PARQUET_FILE,
    MARINE_PARQUET_FILE,
    PROCESSED_WEATHER_FOLDER,
)


RISK_PARQUET_FILE = (
    PROCESSED_WEATHER_FOLDER
    / "operational_weather_risk.parquet"
)


ATMOSPHERIC_REQUIRED_COLUMNS = {
    "forecast_reference_time",
    "forecast_valid_time",
    "forecast_horizon_hours",
    "asset_id",
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "pressure_hpa",
    "wind_speed_kmh",
    "wind_direction_deg",
    "wind_gust_kmh",
    "visibility_m",
    "weather_code",
    "source",
}


MARINE_REQUIRED_COLUMNS = {
    "forecast_reference_time",
    "forecast_valid_time",
    "forecast_horizon_hours",
    "asset_id",
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
    "source",
}


RISK_REQUIRED_COLUMNS = {
    "forecast_reference_time",
    "forecast_valid_time",
    "asset_id",
    "wind_risk_level",
    "gust_risk_level",
    "wave_risk_level",
    "visibility_risk_level",
    "overall_risk_level",
    "operation_recommendation",
    "limiting_parameter",
    "source",
}


def read_parquet(
    path: Path,
    required_columns: set[str],
    dataset_name: str,
) -> pd.DataFrame:
    """
    Read and validate a Silver Parquet dataset.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"{dataset_name} Parquet not found: "
            f"{path.resolve()}"
        )

    logger.info(
        "Reading {} Parquet: {}",
        dataset_name,
        path,
    )

    dataframe = pd.read_parquet(path)

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    if dataframe.empty:
        raise ValueError(
            f"{dataset_name} Parquet is empty."
        )

    for column in [
        "forecast_reference_time",
        "forecast_valid_time",
    ]:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
            utc=True,
        ).dt.tz_localize(None)

    dataframe["asset_id"] = (
        dataframe["asset_id"]
        .astype("string")
        .str.strip()
    )

    dataframe = dataframe.dropna(
        subset=[
            "forecast_reference_time",
            "forecast_valid_time",
            "asset_id",
        ]
    )

    if dataframe.empty:
        raise ValueError(
            f"{dataset_name} contains no valid rows."
        )

    logger.success(
        "{} validated: {} rows",
        dataset_name,
        len(dataframe),
    )

    return dataframe.reset_index(drop=True)


def get_season(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"

    if month in (3, 4, 5):
        return "Spring"

    if month in (6, 7, 8):
        return "Summer"

    return "Autumn"


def load_dim_time(
    connection: Connection,
    dataframes: list[pd.DataFrame],
) -> int:
    """
    Insert every unique forecast-valid timestamp into dim_time.
    """

    timestamps = pd.concat(
        [
            dataframe[
                ["forecast_valid_time"]
            ]
            for dataframe in dataframes
        ],
        ignore_index=True,
    )["forecast_valid_time"]

    timestamps = (
        timestamps
        .drop_duplicates()
        .sort_values()
    )

    statement = text(
        """
        INSERT INTO dim_time
        (
            timestamp,
            date,
            hour,
            month,
            season
        )
        VALUES
        (
            :timestamp,
            :date,
            :hour,
            :month,
            :season
        )
        ON CONFLICT (timestamp)
        DO NOTHING;
        """
    )

    records = []

    for value in timestamps:
        timestamp = pd.Timestamp(value)

        records.append(
            {
                "timestamp":
                    timestamp.to_pydatetime(),

                "date":
                    timestamp.date(),

                "hour":
                    int(timestamp.hour),

                "month":
                    int(timestamp.month),

                "season":
                    get_season(
                        int(timestamp.month)
                    ),
            }
        )

    connection.execute(
        statement,
        records,
    )

    logger.success(
        "dim_time processed for weather forecasts: {} timestamps",
        len(records),
    )

    return len(records)


def get_time_mapping(
    connection: Connection,
    dataframes: list[pd.DataFrame],
) -> dict[pd.Timestamp, int]:
    """
    Resolve forecast-valid timestamps to time_key.
    """

    requested_timestamps = set()

    for dataframe in dataframes:
        requested_timestamps.update(
            pd.Timestamp(value)
            for value in dataframe[
                "forecast_valid_time"
            ].drop_duplicates()
        )

    rows = connection.execute(
        text(
            """
            SELECT
                time_key,
                timestamp
            FROM dim_time;
            """
        )
    ).mappings()

    mapping = {
        pd.Timestamp(row["timestamp"]):
            int(row["time_key"])
        for row in rows
        if pd.Timestamp(row["timestamp"])
        in requested_timestamps
    }

    missing = (
        requested_timestamps
        - set(mapping)
    )

    if missing:
        examples = sorted(missing)[:5]

        raise ValueError(
            "Some forecast timestamps were not found "
            f"in dim_time. Examples: {examples}"
        )

    logger.info(
        "Resolved {} weather time keys",
        len(mapping),
    )

    return mapping


def get_asset_mapping(
    connection: Connection,
) -> dict[str, int]:
    rows = connection.execute(
        text(
            """
            SELECT
                asset_key,
                asset_id
            FROM dim_asset
            WHERE is_active = TRUE;
            """
        )
    ).mappings()

    mapping = {
        str(row["asset_id"]).strip():
            int(row["asset_key"])
        for row in rows
    }

    if not mapping:
        raise ValueError(
            "No active assets found in dim_asset. "
            "Run load_weather_dimensions first."
        )

    logger.info(
        "Resolved {} active assets",
        len(mapping),
    )

    return mapping


def safe_value(value: Any) -> Any:
    """
    Convert pandas missing values into Python None.
    """

    if pd.isna(value):
        return None

    return value


def build_atmospheric_records(
    dataframe: pd.DataFrame,
    time_mapping: dict[pd.Timestamp, int],
    asset_mapping: dict[str, int],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row in dataframe.itertuples(index=False):
        valid_time = pd.Timestamp(
            row.forecast_valid_time
        )

        asset_id = str(
            row.asset_id
        ).strip()

        time_key = time_mapping.get(
            valid_time
        )

        asset_key = asset_mapping.get(
            asset_id
        )

        if time_key is None:
            raise KeyError(
                f"No time_key found for {valid_time}"
            )

        if asset_key is None:
            raise KeyError(
                f"No asset_key found for {asset_id}"
            )

        records.append(
            {
                "time_key":
                    time_key,

                "asset_key":
                    asset_key,

                "forecast_reference_time":
                    pd.Timestamp(
                        row.forecast_reference_time
                    ).to_pydatetime(),

                "forecast_valid_time":
                    valid_time.to_pydatetime(),

                "forecast_horizon_hours":
                    int(
                        row.forecast_horizon_hours
                    ),

                "temperature_c":
                    safe_value(
                        row.temperature_c
                    ),

                "relative_humidity_pct":
                    safe_value(
                        row.relative_humidity_pct
                    ),

                "pressure_hpa":
                    safe_value(
                        row.pressure_hpa
                    ),

                "precipitation_mm":
                    safe_value(
                        row.precipitation_mm
                    ),

                "wind_speed_kmh":
                    safe_value(
                        row.wind_speed_kmh
                    ),

                "wind_direction_deg":
                    safe_value(
                        row.wind_direction_deg
                    ),

                "wind_gust_kmh":
                    safe_value(
                        row.wind_gust_kmh
                    ),

                "visibility_m":
                    safe_value(
                        row.visibility_m
                    ),

                "weather_code":
                    (
                        None
                        if pd.isna(
                            row.weather_code
                        )
                        else int(
                            row.weather_code
                        )
                    ),

                "source":
                    str(row.source).strip(),
            }
        )

    return records


def build_marine_records(
    dataframe: pd.DataFrame,
    time_mapping: dict[pd.Timestamp, int],
    asset_mapping: dict[str, int],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row in dataframe.itertuples(index=False):
        valid_time = pd.Timestamp(
            row.forecast_valid_time
        )

        asset_id = str(
            row.asset_id
        ).strip()

        time_key = time_mapping.get(
            valid_time
        )

        asset_key = asset_mapping.get(
            asset_id
        )

        if time_key is None:
            raise KeyError(
                f"No time_key found for {valid_time}"
            )

        if asset_key is None:
            raise KeyError(
                f"No asset_key found for {asset_id}"
            )

        records.append(
            {
                "time_key":
                    time_key,

                "asset_key":
                    asset_key,

                "forecast_reference_time":
                    pd.Timestamp(
                        row.forecast_reference_time
                    ).to_pydatetime(),

                "forecast_valid_time":
                    valid_time.to_pydatetime(),

                "forecast_horizon_hours":
                    int(
                        row.forecast_horizon_hours
                    ),

                "wave_height_m":
                    safe_value(
                        row.wave_height_m
                    ),

                "wave_direction_deg":
                    safe_value(
                        row.wave_direction_deg
                    ),

                "wave_period_s":
                    safe_value(
                        row.wave_period_s
                    ),

                "wind_wave_height_m":
                    safe_value(
                        row.wind_wave_height_m
                    ),

                "swell_wave_height_m":
                    safe_value(
                        row.swell_wave_height_m
                    ),

                "swell_wave_direction_deg":
                    safe_value(
                        row.swell_wave_direction_deg
                    ),

                "swell_wave_period_s":
                    safe_value(
                        row.swell_wave_period_s
                    ),

                "sea_surface_temperature_c":
                    safe_value(
                        row.sea_surface_temperature_c
                    ),

                "ocean_current_velocity_kmh":
                    safe_value(
                        row.ocean_current_velocity_kmh
                    ),

                "ocean_current_direction_deg":
                    safe_value(
                        row.ocean_current_direction_deg
                    ),

                "source":
                    str(row.source).strip(),
            }
        )

    return records


def build_risk_records(
    dataframe: pd.DataFrame,
    time_mapping: dict[pd.Timestamp, int],
    asset_mapping: dict[str, int],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row in dataframe.itertuples(index=False):
        valid_time = pd.Timestamp(
            row.forecast_valid_time
        )

        asset_id = str(
            row.asset_id
        ).strip()

        time_key = time_mapping.get(
            valid_time
        )

        asset_key = asset_mapping.get(
            asset_id
        )

        if time_key is None:
            raise KeyError(
                f"No time_key found for {valid_time}"
            )

        if asset_key is None:
            raise KeyError(
                f"No asset_key found for {asset_id}"
            )

        limiting_parameter = safe_value(
            row.limiting_parameter
        )

        records.append(
            {
                "time_key":
                    time_key,

                "asset_key":
                    asset_key,

                "forecast_reference_time":
                    pd.Timestamp(
                        row.forecast_reference_time
                    ).to_pydatetime(),

                "forecast_valid_time":
                    valid_time.to_pydatetime(),

                "wind_risk_level":
                    str(
                        row.wind_risk_level
                    ).strip(),

                "gust_risk_level":
                    str(
                        row.gust_risk_level
                    ).strip(),

                "wave_risk_level":
                    str(
                        row.wave_risk_level
                    ).strip(),

                "visibility_risk_level":
                    str(
                        row.visibility_risk_level
                    ).strip(),

                "overall_risk_level":
                    str(
                        row.overall_risk_level
                    ).strip(),

                "operation_recommendation":
                    str(
                        row.operation_recommendation
                    ).strip(),

                "limiting_parameter":
                    (
                        None
                        if limiting_parameter is None
                        else str(
                            limiting_parameter
                        ).strip()
                    ),

                "source":
                    str(row.source).strip(),
            }
        )

    return records


def load_atmospheric_facts(
    connection: Connection,
    records: list[dict[str, Any]],
) -> int:
    statement = text(
        """
        INSERT INTO fact_weather_forecast
        (
            time_key,
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            forecast_horizon_hours,
            temperature_c,
            relative_humidity_pct,
            pressure_hpa,
            precipitation_mm,
            wind_speed_kmh,
            wind_direction_deg,
            wind_gust_kmh,
            visibility_m,
            weather_code,
            source
        )
        VALUES
        (
            :time_key,
            :asset_key,
            :forecast_reference_time,
            :forecast_valid_time,
            :forecast_horizon_hours,
            :temperature_c,
            :relative_humidity_pct,
            :pressure_hpa,
            :precipitation_mm,
            :wind_speed_kmh,
            :wind_direction_deg,
            :wind_gust_kmh,
            :visibility_m,
            :weather_code,
            :source
        )
        ON CONFLICT
        (
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            source
        )
        DO UPDATE SET
            time_key =
                EXCLUDED.time_key,

            forecast_horizon_hours =
                EXCLUDED.forecast_horizon_hours,

            temperature_c =
                EXCLUDED.temperature_c,

            relative_humidity_pct =
                EXCLUDED.relative_humidity_pct,

            pressure_hpa =
                EXCLUDED.pressure_hpa,

            precipitation_mm =
                EXCLUDED.precipitation_mm,

            wind_speed_kmh =
                EXCLUDED.wind_speed_kmh,

            wind_direction_deg =
                EXCLUDED.wind_direction_deg,

            wind_gust_kmh =
                EXCLUDED.wind_gust_kmh,

            visibility_m =
                EXCLUDED.visibility_m,

            weather_code =
                EXCLUDED.weather_code,

            ingestion_time =
                CURRENT_TIMESTAMP;
        """
    )

    connection.execute(
        statement,
        records,
    )

    logger.success(
        "fact_weather_forecast processed: {} rows",
        len(records),
    )

    return len(records)


def load_marine_facts(
    connection: Connection,
    records: list[dict[str, Any]],
) -> int:
    statement = text(
        """
        INSERT INTO fact_marine_forecast
        (
            time_key,
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            forecast_horizon_hours,
            wave_height_m,
            wave_direction_deg,
            wave_period_s,
            wind_wave_height_m,
            swell_wave_height_m,
            swell_wave_direction_deg,
            swell_wave_period_s,
            sea_surface_temperature_c,
            ocean_current_velocity_kmh,
            ocean_current_direction_deg,
            source
        )
        VALUES
        (
            :time_key,
            :asset_key,
            :forecast_reference_time,
            :forecast_valid_time,
            :forecast_horizon_hours,
            :wave_height_m,
            :wave_direction_deg,
            :wave_period_s,
            :wind_wave_height_m,
            :swell_wave_height_m,
            :swell_wave_direction_deg,
            :swell_wave_period_s,
            :sea_surface_temperature_c,
            :ocean_current_velocity_kmh,
            :ocean_current_direction_deg,
            :source
        )
        ON CONFLICT
        (
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            source
        )
        DO UPDATE SET
            time_key =
                EXCLUDED.time_key,

            forecast_horizon_hours =
                EXCLUDED.forecast_horizon_hours,

            wave_height_m =
                EXCLUDED.wave_height_m,

            wave_direction_deg =
                EXCLUDED.wave_direction_deg,

            wave_period_s =
                EXCLUDED.wave_period_s,

            wind_wave_height_m =
                EXCLUDED.wind_wave_height_m,

            swell_wave_height_m =
                EXCLUDED.swell_wave_height_m,

            swell_wave_direction_deg =
                EXCLUDED.swell_wave_direction_deg,

            swell_wave_period_s =
                EXCLUDED.swell_wave_period_s,

            sea_surface_temperature_c =
                EXCLUDED.sea_surface_temperature_c,

            ocean_current_velocity_kmh =
                EXCLUDED.ocean_current_velocity_kmh,

            ocean_current_direction_deg =
                EXCLUDED.ocean_current_direction_deg,

            ingestion_time =
                CURRENT_TIMESTAMP;
        """
    )

    connection.execute(
        statement,
        records,
    )

    logger.success(
        "fact_marine_forecast processed: {} rows",
        len(records),
    )

    return len(records)


def load_risk_facts(
    connection: Connection,
    records: list[dict[str, Any]],
) -> int:
    statement = text(
        """
        INSERT INTO fact_operational_weather_risk
        (
            time_key,
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            wind_risk_level,
            gust_risk_level,
            wave_risk_level,
            visibility_risk_level,
            overall_risk_level,
            operation_recommendation,
            limiting_parameter,
            source
        )
        VALUES
        (
            :time_key,
            :asset_key,
            :forecast_reference_time,
            :forecast_valid_time,
            :wind_risk_level,
            :gust_risk_level,
            :wave_risk_level,
            :visibility_risk_level,
            :overall_risk_level,
            :operation_recommendation,
            :limiting_parameter,
            :source
        )
        ON CONFLICT
        (
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            source
        )
        DO UPDATE SET
            time_key =
                EXCLUDED.time_key,

            wind_risk_level =
                EXCLUDED.wind_risk_level,

            gust_risk_level =
                EXCLUDED.gust_risk_level,

            wave_risk_level =
                EXCLUDED.wave_risk_level,

            visibility_risk_level =
                EXCLUDED.visibility_risk_level,

            overall_risk_level =
                EXCLUDED.overall_risk_level,

            operation_recommendation =
                EXCLUDED.operation_recommendation,

            limiting_parameter =
                EXCLUDED.limiting_parameter,

            ingestion_time =
                CURRENT_TIMESTAMP;
        """
    )

    connection.execute(
        statement,
        records,
    )

    logger.success(
        "fact_operational_weather_risk processed: {} rows",
        len(records),
    )

    return len(records)


def load_weather_facts() -> dict[str, int]:
    logger.info(
        "Starting operational weather fact loading"
    )

    atmospheric = read_parquet(
        path=ATMOSPHERIC_PARQUET_FILE,
        required_columns=
            ATMOSPHERIC_REQUIRED_COLUMNS,
        dataset_name=
            "Atmospheric forecast",
    )

    marine = read_parquet(
        path=MARINE_PARQUET_FILE,
        required_columns=
            MARINE_REQUIRED_COLUMNS,
        dataset_name=
            "Marine forecast",
    )

    risk = read_parquet(
        path=RISK_PARQUET_FILE,
        required_columns=
            RISK_REQUIRED_COLUMNS,
        dataset_name=
            "Operational weather risk",
    )

    engine = get_engine()

    with engine.begin() as connection:
        load_dim_time(
            connection=connection,
            dataframes=[
                atmospheric,
                marine,
                risk,
            ],
        )

        time_mapping = get_time_mapping(
            connection=connection,
            dataframes=[
                atmospheric,
                marine,
                risk,
            ],
        )

        asset_mapping = get_asset_mapping(
            connection
        )

        atmospheric_records = (
            build_atmospheric_records(
                dataframe=atmospheric,
                time_mapping=time_mapping,
                asset_mapping=asset_mapping,
            )
        )

        marine_records = (
            build_marine_records(
                dataframe=marine,
                time_mapping=time_mapping,
                asset_mapping=asset_mapping,
            )
        )

        risk_records = build_risk_records(
            dataframe=risk,
            time_mapping=time_mapping,
            asset_mapping=asset_mapping,
        )

        atmospheric_count = (
            load_atmospheric_facts(
                connection=connection,
                records=atmospheric_records,
            )
        )

        marine_count = (
            load_marine_facts(
                connection=connection,
                records=marine_records,
            )
        )

        risk_count = load_risk_facts(
            connection=connection,
            records=risk_records,
        )

    logger.success(
        "Operational weather facts loaded successfully"
    )

    return {
        "atmospheric":
            atmospheric_count,

        "marine":
            marine_count,

        "risk":
            risk_count,
    }


def main() -> None:
    results = load_weather_facts()

    print("\nWeather warehouse load results:")

    for dataset, row_count in results.items():
        print(
            f"{dataset}: {row_count} rows"
        )


if __name__ == "__main__":
    main()
    