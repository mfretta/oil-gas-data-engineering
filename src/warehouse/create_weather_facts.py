from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_FACT_WEATHER_FORECAST_SQL = """
CREATE TABLE IF NOT EXISTS fact_weather_forecast
(
    weather_forecast_key BIGSERIAL PRIMARY KEY,

    time_key INTEGER NOT NULL,

    asset_key INTEGER NOT NULL,

    forecast_reference_time TIMESTAMP NOT NULL,

    forecast_valid_time TIMESTAMP NOT NULL,

    forecast_horizon_hours INTEGER NOT NULL,

    temperature_c NUMERIC(8, 3),

    relative_humidity_pct NUMERIC(8, 3),

    pressure_hpa NUMERIC(10, 3),

    precipitation_mm NUMERIC(10, 3),

    wind_speed_kmh NUMERIC(10, 3),

    wind_direction_deg NUMERIC(8, 3),

    wind_gust_kmh NUMERIC(10, 3),

    visibility_m NUMERIC(12, 3),

    weather_code INTEGER,

    source VARCHAR(100) NOT NULL,

    ingestion_time TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_weather_forecast_time
        FOREIGN KEY (time_key)
        REFERENCES dim_time(time_key),

    CONSTRAINT fk_weather_forecast_asset
        FOREIGN KEY (asset_key)
        REFERENCES dim_asset(asset_key),

    CONSTRAINT chk_weather_forecast_horizon
        CHECK (forecast_horizon_hours >= 0),

    CONSTRAINT chk_relative_humidity
        CHECK (
            relative_humidity_pct IS NULL
            OR relative_humidity_pct BETWEEN 0 AND 100
        ),

    CONSTRAINT uq_weather_forecast
        UNIQUE
        (
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            source
        )
);
"""


CREATE_FACT_MARINE_FORECAST_SQL = """
CREATE TABLE IF NOT EXISTS fact_marine_forecast
(
    marine_forecast_key BIGSERIAL PRIMARY KEY,

    time_key INTEGER NOT NULL,

    asset_key INTEGER NOT NULL,

    forecast_reference_time TIMESTAMP NOT NULL,

    forecast_valid_time TIMESTAMP NOT NULL,

    forecast_horizon_hours INTEGER NOT NULL,

    wave_height_m NUMERIC(8, 3),

    wave_direction_deg NUMERIC(8, 3),

    wave_period_s NUMERIC(8, 3),

    wind_wave_height_m NUMERIC(8, 3),

    swell_wave_height_m NUMERIC(8, 3),

    swell_wave_direction_deg NUMERIC(8, 3),

    swell_wave_period_s NUMERIC(8, 3),

    sea_surface_temperature_c NUMERIC(8, 3),

    ocean_current_velocity_kmh NUMERIC(8, 3),

    ocean_current_direction_deg NUMERIC(8, 3),

    source VARCHAR(100) NOT NULL,

    ingestion_time TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_marine_forecast_time
        FOREIGN KEY (time_key)
        REFERENCES dim_time(time_key),

    CONSTRAINT fk_marine_forecast_asset
        FOREIGN KEY (asset_key)
        REFERENCES dim_asset(asset_key),

    CONSTRAINT chk_marine_forecast_horizon
        CHECK (forecast_horizon_hours >= 0),

    CONSTRAINT chk_wave_height
        CHECK (
            wave_height_m IS NULL
            OR wave_height_m >= 0
        ),

    CONSTRAINT uq_marine_forecast
        UNIQUE
        (
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            source
        )
);
"""


CREATE_FACT_OPERATIONAL_RISK_SQL = """
CREATE TABLE IF NOT EXISTS fact_operational_weather_risk
(
    operational_risk_key BIGSERIAL PRIMARY KEY,

    time_key INTEGER NOT NULL,

    asset_key INTEGER NOT NULL,

    forecast_reference_time TIMESTAMP NOT NULL,

    forecast_valid_time TIMESTAMP NOT NULL,

    wind_risk_level VARCHAR(20) NOT NULL,

    gust_risk_level VARCHAR(20) NOT NULL,

    wave_risk_level VARCHAR(20) NOT NULL,

    visibility_risk_level VARCHAR(20) NOT NULL,

    overall_risk_level VARCHAR(20) NOT NULL,

    operation_recommendation VARCHAR(255) NOT NULL,

    limiting_parameter VARCHAR(100),

    source VARCHAR(100) NOT NULL,

    ingestion_time TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_operational_risk_time
        FOREIGN KEY (time_key)
        REFERENCES dim_time(time_key),

    CONSTRAINT fk_operational_risk_asset
        FOREIGN KEY (asset_key)
        REFERENCES dim_asset(asset_key),

    CONSTRAINT chk_overall_risk
        CHECK (
            overall_risk_level IN
            ('GREEN', 'AMBER', 'RED', 'UNKNOWN')
        ),

    CONSTRAINT uq_operational_weather_risk
        UNIQUE
        (
            asset_key,
            forecast_reference_time,
            forecast_valid_time,
            source
        )
);
"""


CREATE_WEATHER_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS
    idx_weather_forecast_asset_time
ON fact_weather_forecast
(
    asset_key,
    forecast_valid_time
);

CREATE INDEX IF NOT EXISTS
    idx_marine_forecast_asset_time
ON fact_marine_forecast
(
    asset_key,
    forecast_valid_time
);

CREATE INDEX IF NOT EXISTS
    idx_operational_risk_asset_time
ON fact_operational_weather_risk
(
    asset_key,
    forecast_valid_time
);

CREATE INDEX IF NOT EXISTS
    idx_operational_risk_level
ON fact_operational_weather_risk
(
    overall_risk_level
);
"""


def create_weather_facts() -> None:
    logger.info(
        "Creating operational weather fact tables"
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(CREATE_FACT_WEATHER_FORECAST_SQL)
        )

        connection.execute(
            text(CREATE_FACT_MARINE_FORECAST_SQL)
        )

        connection.execute(
            text(CREATE_FACT_OPERATIONAL_RISK_SQL)
        )

        connection.execute(
            text(CREATE_WEATHER_INDEXES_SQL)
        )

    logger.success(
        "Operational weather fact tables created"
    )


def main() -> None:
    create_weather_facts()


if __name__ == "__main__":
    main()