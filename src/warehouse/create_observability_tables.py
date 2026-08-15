from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_PIPELINE_RUN_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fact_pipeline_run
(
    pipeline_run_key BIGSERIAL PRIMARY KEY,

    pipeline_name VARCHAR(100) NOT NULL,

    started_at TIMESTAMP NOT NULL,

    finished_at TIMESTAMP,

    duration_seconds NUMERIC(12,3),

    status VARCHAR(20) NOT NULL,

    error_message TEXT,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_pipeline_status
        CHECK (
            status IN (
                'RUNNING',
                'SUCCESS',
                'FAILED'
            )
        )
);
"""


CREATE_DATA_QUALITY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fact_data_quality_check
(
    quality_check_key BIGSERIAL PRIMARY KEY,

    pipeline_run_key BIGINT NOT NULL,

    check_name VARCHAR(200) NOT NULL,

    passed BOOLEAN NOT NULL,

    check_value TEXT,

    expectation TEXT,

    details TEXT,

    checked_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_quality_pipeline_run
        FOREIGN KEY (
            pipeline_run_key
        )
        REFERENCES fact_pipeline_run (
            pipeline_run_key
        )
        ON DELETE CASCADE
);
"""


CREATE_INDEXES_SQL = [
    """
    CREATE INDEX IF NOT EXISTS
        idx_pipeline_run_started_at
    ON fact_pipeline_run (
        started_at
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS
        idx_pipeline_run_status
    ON fact_pipeline_run (
        status
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS
        idx_quality_pipeline_run
    ON fact_data_quality_check (
        pipeline_run_key
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS
        idx_quality_passed
    ON fact_data_quality_check (
        passed
    );
    """,
]


def create_observability_tables() -> None:
    """
    Create pipeline observability and data-quality
    persistence tables if they do not already exist.
    """

    logger.info(
        "Creating observability tables"
    )

    engine = get_engine()

    with engine.begin() as connection:

        connection.execute(
            text(
                CREATE_PIPELINE_RUN_TABLE_SQL
            )
        )

        connection.execute(
            text(
                CREATE_DATA_QUALITY_TABLE_SQL
            )
        )

        for sql in CREATE_INDEXES_SQL:
            connection.execute(
                text(sql)
            )

    logger.success(
        "Observability tables ready"
    )


def main() -> None:
    create_observability_tables()


if __name__ == "__main__":
    main()