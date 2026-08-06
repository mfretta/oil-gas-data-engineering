from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_FACT_RIG_COUNT_SQL = """
CREATE TABLE IF NOT EXISTS fact_rig_count
(
    rig_count_key BIGSERIAL PRIMARY KEY,

    time_key INTEGER NOT NULL,

    country_key INTEGER NOT NULL,

    rig_classification_key INTEGER NOT NULL,

    rig_count NUMERIC(12, 4) NOT NULL,

    source VARCHAR(100) NOT NULL,

    source_file VARCHAR(255) NOT NULL,

    source_ingestion_time TIMESTAMP NOT NULL,

    warehouse_loaded_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_rig_count_time
        FOREIGN KEY (time_key)
        REFERENCES dim_time(time_key),

    CONSTRAINT fk_rig_count_country
        FOREIGN KEY (country_key)
        REFERENCES dim_country(country_key),

    CONSTRAINT fk_rig_count_classification
        FOREIGN KEY (rig_classification_key)
        REFERENCES dim_rig_classification(
            rig_classification_key
        ),

    CONSTRAINT chk_rig_count_non_negative
        CHECK (rig_count >= 0),

    CONSTRAINT uq_rig_count_observation
        UNIQUE
        (
            time_key,
            country_key,
            rig_classification_key,
            source
        )
);
"""


CREATE_RIG_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS
    idx_fact_rig_count_time
ON fact_rig_count(time_key);

CREATE INDEX IF NOT EXISTS
    idx_fact_rig_count_country
ON fact_rig_count(country_key);

CREATE INDEX IF NOT EXISTS
    idx_fact_rig_count_classification
ON fact_rig_count(rig_classification_key);

CREATE INDEX IF NOT EXISTS
    idx_fact_rig_count_country_time
ON fact_rig_count(country_key, time_key);
"""


def create_rig_facts() -> None:
    logger.info("Creating fact_rig_count")

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(CREATE_FACT_RIG_COUNT_SQL)
        )

        connection.execute(
            text(CREATE_RIG_INDEXES_SQL)
        )

    logger.success(
        "fact_rig_count and indexes created successfully"
    )


def main() -> None:
    create_rig_facts()


if __name__ == "__main__":
    main()