from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_DIM_COUNTRY_SQL = """
CREATE TABLE IF NOT EXISTS dim_country
(
    country_key SERIAL PRIMARY KEY,

    country_name VARCHAR(150) NOT NULL UNIQUE,

    region VARCHAR(100) NOT NULL,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);
"""


CREATE_DIM_RIG_CLASSIFICATION_SQL = """
CREATE TABLE IF NOT EXISTS dim_rig_classification
(
    rig_classification_key SERIAL PRIMARY KEY,

    drilling_target VARCHAR(50) NOT NULL,

    location_type VARCHAR(50) NOT NULL,

    rig_status VARCHAR(50) NOT NULL,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_rig_classification
        UNIQUE
        (
            drilling_target,
            location_type,
            rig_status
        )
);
"""


def create_rig_dimensions() -> None:
    logger.info("Creating rig-count dimensions")

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(CREATE_DIM_COUNTRY_SQL)
        )

        connection.execute(
            text(CREATE_DIM_RIG_CLASSIFICATION_SQL)
        )

    logger.success(
        "Rig-count dimensions created successfully"
    )


def main() -> None:
    create_rig_dimensions()


if __name__ == "__main__":
    main()