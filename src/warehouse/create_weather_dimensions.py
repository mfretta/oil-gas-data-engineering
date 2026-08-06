from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_DIM_ASSET_SQL = """
CREATE TABLE IF NOT EXISTS dim_asset
(
    asset_key SERIAL PRIMARY KEY,

    asset_id VARCHAR(50) NOT NULL UNIQUE,

    asset_name VARCHAR(150) NOT NULL,

    asset_type VARCHAR(50) NOT NULL,

    operator_name VARCHAR(150),

    location_key INTEGER NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    max_wind_kmh NUMERIC(8, 2),
    max_gust_kmh NUMERIC(8, 2),
    max_wave_height_m NUMERIC(8, 2),
    minimum_visibility_m NUMERIC(10, 2),

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_asset_location
        FOREIGN KEY (location_key)
        REFERENCES dim_location(location_key)
);
"""


CREATE_ASSET_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_dim_asset_location
    ON dim_asset(location_key);

CREATE INDEX IF NOT EXISTS idx_dim_asset_active
    ON dim_asset(is_active);
"""


def create_weather_dimensions() -> None:
    logger.info("Creating weather-related dimensions")

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(CREATE_DIM_ASSET_SQL)
        )

        connection.execute(
            text(CREATE_ASSET_INDEXES_SQL)
        )

    logger.success(
        "Weather-related dimensions created successfully"
    )


def main() -> None:
    create_weather_dimensions()


if __name__ == "__main__":
    main()