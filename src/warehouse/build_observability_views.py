from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_LATEST_PIPELINE_RUN_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_latest_pipeline_run AS

SELECT
    pipeline_run_key,
    pipeline_name,
    started_at,
    finished_at,
    duration_seconds,
    status,
    error_message

FROM fact_pipeline_run

ORDER BY started_at DESC

LIMIT 1;
"""


CREATE_LATEST_QUALITY_SUMMARY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_latest_quality_summary AS

WITH latest_run AS
(
    SELECT
        pipeline_run_key
    FROM fact_pipeline_run
    ORDER BY started_at DESC
    LIMIT 1
)

SELECT
    q.pipeline_run_key,

    COUNT(*) AS total_checks,

    COUNT(*) FILTER
    (
        WHERE q.passed = TRUE
    ) AS passed_checks,

    COUNT(*) FILTER
    (
        WHERE q.passed = FALSE
    ) AS failed_checks,

    ROUND(
        (
            COUNT(*) FILTER
            (
                WHERE q.passed = TRUE
            )::NUMERIC
            /
            NULLIF(
                COUNT(*),
                0
            )
        ) * 100,
        2
    ) AS pass_rate_percent

FROM fact_data_quality_check AS q

INNER JOIN latest_run AS r
    ON r.pipeline_run_key =
       q.pipeline_run_key

GROUP BY
    q.pipeline_run_key;
"""


CREATE_LATEST_QUALITY_CHECKS_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_latest_quality_checks AS

WITH latest_run AS
(
    SELECT
        pipeline_run_key
    FROM fact_pipeline_run
    ORDER BY started_at DESC
    LIMIT 1
)

SELECT
    q.quality_check_key,
    q.pipeline_run_key,
    q.check_name,
    q.passed,
    q.check_value,
    q.expectation,
    q.details,
    q.checked_at

FROM fact_data_quality_check AS q

INNER JOIN latest_run AS r
    ON r.pipeline_run_key =
       q.pipeline_run_key

ORDER BY
    q.passed ASC,
    q.check_name;
"""


CREATE_PIPELINE_HISTORY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_pipeline_run_history AS

SELECT
    p.pipeline_run_key,
    p.pipeline_name,
    p.started_at,
    p.finished_at,
    p.duration_seconds,
    p.status,
    p.error_message,

    COUNT(q.quality_check_key)
        AS total_checks,

    COUNT(q.quality_check_key) FILTER
    (
        WHERE q.passed = TRUE
    ) AS passed_checks,

    COUNT(q.quality_check_key) FILTER
    (
        WHERE q.passed = FALSE
    ) AS failed_checks

FROM fact_pipeline_run AS p

LEFT JOIN fact_data_quality_check AS q
    ON q.pipeline_run_key =
       p.pipeline_run_key

GROUP BY
    p.pipeline_run_key,
    p.pipeline_name,
    p.started_at,
    p.finished_at,
    p.duration_seconds,
    p.status,
    p.error_message

ORDER BY
    p.started_at DESC;
"""


def build_observability_views() -> None:
    logger.info(
        "Creating pipeline observability views"
    )

    engine = get_engine()

    with engine.begin() as connection:

        connection.execute(
            text(
                CREATE_LATEST_PIPELINE_RUN_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_LATEST_QUALITY_SUMMARY_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_LATEST_QUALITY_CHECKS_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_PIPELINE_HISTORY_VIEW_SQL
            )
        )

    logger.success(
        "Pipeline observability views created successfully"
    )


def main() -> None:
    build_observability_views()


if __name__ == "__main__":
    main()