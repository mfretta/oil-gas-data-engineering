from __future__ import annotations

from datetime import datetime
from typing import Iterable

from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


def start_pipeline_run(
    pipeline_name: str,
) -> int:
    """
    Insert a RUNNING pipeline record and return its key.
    """

    engine = get_engine()

    query = text(
        """
        INSERT INTO fact_pipeline_run
        (
            pipeline_name,
            started_at,
            status
        )
        VALUES
        (
            :pipeline_name,
            CURRENT_TIMESTAMP,
            'RUNNING'
        )
        RETURNING pipeline_run_key;
        """
    )

    with engine.begin() as connection:
        pipeline_run_key = connection.execute(
            query,
            {
                "pipeline_name": pipeline_name,
            },
        ).scalar_one()

    logger.info(
        "Pipeline observability started: {} | run_key={}",
        pipeline_name,
        pipeline_run_key,
    )

    return int(pipeline_run_key)


def finish_pipeline_run_success(
    pipeline_run_key: int,
) -> None:
    """
    Mark a pipeline run as SUCCESS.
    """

    engine = get_engine()

    query = text(
        """
        UPDATE fact_pipeline_run
        SET
            finished_at = CURRENT_TIMESTAMP,
            duration_seconds =
                EXTRACT(
                    EPOCH FROM
                    (
                        CURRENT_TIMESTAMP
                        - started_at
                    )
                ),
            status = 'SUCCESS',
            error_message = NULL
        WHERE pipeline_run_key =
            :pipeline_run_key;
        """
    )

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "pipeline_run_key":
                    pipeline_run_key,
            },
        )

    logger.success(
        "Pipeline run marked SUCCESS | run_key={}",
        pipeline_run_key,
    )


def finish_pipeline_run_failed(
    pipeline_run_key: int,
    error_message: str,
) -> None:
    """
    Mark a pipeline run as FAILED.
    """

    engine = get_engine()

    query = text(
        """
        UPDATE fact_pipeline_run
        SET
            finished_at = CURRENT_TIMESTAMP,
            duration_seconds =
                EXTRACT(
                    EPOCH FROM
                    (
                        CURRENT_TIMESTAMP
                        - started_at
                    )
                ),
            status = 'FAILED',
            error_message = :error_message
        WHERE pipeline_run_key =
            :pipeline_run_key;
        """
    )

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "pipeline_run_key":
                    pipeline_run_key,
                "error_message":
                    error_message,
            },
        )

    logger.error(
        "Pipeline run marked FAILED | run_key={}",
        pipeline_run_key,
    )


def save_quality_results(
    pipeline_run_key: int,
    results: Iterable,
) -> int:
    """
    Persist warehouse validation results.

    Expects objects with:
    - name
    - passed
    - value
    - expectation
    - details
    """

    records = []

    for result in results:
        records.append(
            {
                "pipeline_run_key":
                    pipeline_run_key,

                "check_name":
                    str(result.name),

                "passed":
                    bool(result.passed),

                "check_value":
                    str(result.value),

                "expectation":
                    str(result.expectation),

                "details":
                    (
                        str(result.details)
                        if result.details
                        else None
                    ),
            }
        )

    if not records:
        logger.warning(
            "No quality-check results to persist."
        )

        return 0

    query = text(
        """
        INSERT INTO fact_data_quality_check
        (
            pipeline_run_key,
            check_name,
            passed,
            check_value,
            expectation,
            details,
            checked_at
        )
        VALUES
        (
            :pipeline_run_key,
            :check_name,
            :passed,
            :check_value,
            :expectation,
            :details,
            CURRENT_TIMESTAMP
        );
        """
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            query,
            records,
        )

    logger.success(
        "Persisted {} data-quality checks for run_key={}",
        len(records),
        pipeline_run_key,
    )

    return len(records)


def get_latest_pipeline_run() -> dict | None:
    """
    Return the latest pipeline execution.
    """

    engine = get_engine()

    query = text(
        """
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
    )

    with engine.connect() as connection:
        row = connection.execute(
            query
        ).mappings().first()

    if row is None:
        return None

    return dict(row)


def get_latest_quality_summary() -> dict:
    """
    Return quality-check summary for latest pipeline run.
    """

    engine = get_engine()

    query = text(
        """
        WITH latest_run AS
        (
            SELECT pipeline_run_key
            FROM fact_pipeline_run
            ORDER BY started_at DESC
            LIMIT 1
        )

        SELECT
            COUNT(*) AS total_checks,

            COUNT(*) FILTER
            (
                WHERE passed = TRUE
            ) AS passed_checks,

            COUNT(*) FILTER
            (
                WHERE passed = FALSE
            ) AS failed_checks

        FROM fact_data_quality_check AS q

        INNER JOIN latest_run AS r
            ON r.pipeline_run_key =
               q.pipeline_run_key;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            query
        ).mappings().first()

    if row is None:
        return {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
        }

    return dict(row)