from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


# ============================================================
# DIM LOCATION
# ============================================================

CREATE_DIM_LOCATION_SQL = """
CREATE TABLE IF NOT EXISTS dim_location
(
    location_key SERIAL PRIMARY KEY,

    location_id VARCHAR(50) NOT NULL UNIQUE,

    location_name VARCHAR(150) NOT NULL,

    country VARCHAR(100),

    latitude NUMERIC(9, 6),

    longitude NUMERIC(9, 6),

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);
"""


# ============================================================
# DIM TIME
# ============================================================

CREATE_DIM_TIME_SQL = """
CREATE TABLE IF NOT EXISTS dim_time
(
    time_key SERIAL PRIMARY KEY,

    timestamp TIMESTAMP NOT NULL UNIQUE,

    date DATE NOT NULL,

    hour INTEGER NOT NULL,

    month INTEGER NOT NULL,

    season VARCHAR(20),

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_dim_time_hour
        CHECK (
            hour BETWEEN 0 AND 23
        ),

    CONSTRAINT chk_dim_time_month
        CHECK (
            month BETWEEN 1 AND 12
        )
);
"""


# ============================================================
# DIM ASSET
# ============================================================

CREATE_DIM_ASSET_SQL = """
CREATE TABLE IF NOT EXISTS dim_asset
(
    asset_key SERIAL PRIMARY KEY,

    asset_id VARCHAR(50) NOT NULL UNIQUE,

    asset_name VARCHAR(150) NOT NULL,

    asset_type VARCHAR(50) NOT NULL,

    operator_name VARCHAR(150),

    location_key INTEGER NOT NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    max_wind_kmh NUMERIC(8, 2),

    max_gust_kmh NUMERIC(8, 2),

    max_wave_height_m NUMERIC(8, 2),

    minimum_visibility_m NUMERIC(10, 2),

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_asset_location
        FOREIGN KEY (
            location_key
        )
        REFERENCES dim_location(
            location_key
        )
);
"""


# ============================================================
# MIGRATIONS
# ============================================================

ALTER_DIM_LOCATION_SQL = [
    """
    ALTER TABLE dim_location
    ADD COLUMN IF NOT EXISTS created_at
    TIMESTAMP NOT NULL
    DEFAULT CURRENT_TIMESTAMP;
    """,

    """
    ALTER TABLE dim_location
    ADD COLUMN IF NOT EXISTS updated_at
    TIMESTAMP NOT NULL
    DEFAULT CURRENT_TIMESTAMP;
    """,
]


ALTER_DIM_TIME_SQL = [
    """
    ALTER TABLE dim_time
    ADD COLUMN IF NOT EXISTS date DATE;
    """,

    """
    ALTER TABLE dim_time
    ADD COLUMN IF NOT EXISTS hour INTEGER;
    """,

    """
    ALTER TABLE dim_time
    ADD COLUMN IF NOT EXISTS month INTEGER;
    """,

    """
    ALTER TABLE dim_time
    ADD COLUMN IF NOT EXISTS season VARCHAR(20);
    """,

    """
    ALTER TABLE dim_time
    ADD COLUMN IF NOT EXISTS created_at
    TIMESTAMP NOT NULL
    DEFAULT CURRENT_TIMESTAMP;
    """,
]


ALTER_DIM_ASSET_SQL = [
    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS asset_type
    VARCHAR(50);
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS operator_name
    VARCHAR(150);
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS location_key
    INTEGER;
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS is_active
    BOOLEAN NOT NULL
    DEFAULT TRUE;
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS max_wind_kmh
    NUMERIC(8, 2);
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS max_gust_kmh
    NUMERIC(8, 2);
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS max_wave_height_m
    NUMERIC(8, 2);
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS minimum_visibility_m
    NUMERIC(10, 2);
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS created_at
    TIMESTAMP NOT NULL
    DEFAULT CURRENT_TIMESTAMP;
    """,

    """
    ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS updated_at
    TIMESTAMP NOT NULL
    DEFAULT CURRENT_TIMESTAMP;
    """,
]


# ============================================================
# INDEXES
# ============================================================

CREATE_INDEXES_SQL = [
    """
    CREATE INDEX IF NOT EXISTS
        idx_dim_location_location_id
    ON dim_location(
        location_id
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS
        idx_dim_time_timestamp
    ON dim_time(
        timestamp
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS
        idx_dim_time_date
    ON dim_time(
        date
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS
        idx_dim_asset_asset_id
    ON dim_asset(
        asset_id
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS
        idx_dim_asset_location_key
    ON dim_asset(
        location_key
    );
    """,
]


# ============================================================
# CREATE DIMENSIONS
# ============================================================

def create_weather_dimensions() -> None:
    """
    Create all dimensions required by the offshore
    weather warehouse.

    Dependency order:

    1. dim_location
    2. dim_time
    3. dim_asset
    """

    logger.info(
        "Creating weather dimensions"
    )

    engine = get_engine()

    with engine.begin() as connection:

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        logger.info(
            "Creating dim_location"
        )

        connection.execute(
            text(
                CREATE_DIM_LOCATION_SQL
            )
        )

        for sql in ALTER_DIM_LOCATION_SQL:
            connection.execute(
                text(sql)
            )

        # ----------------------------------------------------
        # TIME
        # ----------------------------------------------------

        logger.info(
            "Creating dim_time"
        )

        connection.execute(
            text(
                CREATE_DIM_TIME_SQL
            )
        )

        for sql in ALTER_DIM_TIME_SQL:
            connection.execute(
                text(sql)
            )

        # ----------------------------------------------------
        # ASSET
        # ----------------------------------------------------

        logger.info(
            "Creating dim_asset"
        )

        connection.execute(
            text(
                CREATE_DIM_ASSET_SQL
            )
        )

        for sql in ALTER_DIM_ASSET_SQL:
            connection.execute(
                text(sql)
            )

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        logger.info(
            "Creating weather dimension indexes"
        )

        for sql in CREATE_INDEXES_SQL:
            connection.execute(
                text(sql)
            )

    logger.success(
        "Weather dimensions ready"
    )


# ============================================================
# ENTRY POINT
# ============================================================

def main() -> None:
    create_weather_dimensions()


if __name__ == "__main__":
    main()