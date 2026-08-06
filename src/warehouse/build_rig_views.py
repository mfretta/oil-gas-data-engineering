from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_RIG_COUNT_HISTORY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_rig_count_history AS
SELECT
    f.rig_count_key,

    t.time_key,
    t.timestamp,
    t.date,
    t.month,
    t.season,

    c.country_key,
    c.country_name,
    c.region,

    rc.rig_classification_key,
    rc.drilling_target,
    rc.location_type,
    rc.rig_status,

    f.rig_count,
    f.source,
    f.source_file,
    f.source_ingestion_time,
    f.warehouse_loaded_at

FROM fact_rig_count AS f

INNER JOIN dim_time AS t
    ON t.time_key = f.time_key

INNER JOIN dim_country AS c
    ON c.country_key = f.country_key

INNER JOIN dim_rig_classification AS rc
    ON rc.rig_classification_key =
       f.rig_classification_key;
"""


CREATE_RIG_COUNT_COUNTRY_MONTHLY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_rig_count_country_monthly AS
SELECT
    t.date,

    c.region,
    c.country_name,

    rc.drilling_target,
    rc.location_type,
    rc.rig_status,

    SUM(f.rig_count) AS rig_count,

    f.source

FROM fact_rig_count AS f

INNER JOIN dim_time AS t
    ON t.time_key = f.time_key

INNER JOIN dim_country AS c
    ON c.country_key = f.country_key

INNER JOIN dim_rig_classification AS rc
    ON rc.rig_classification_key =
       f.rig_classification_key

GROUP BY
    t.date,
    c.region,
    c.country_name,
    rc.drilling_target,
    rc.location_type,
    rc.rig_status,
    f.source;
"""


CREATE_RIG_COUNT_REGION_MONTHLY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_rig_count_region_monthly AS
SELECT
    t.date,

    c.region,

    rc.drilling_target,
    rc.location_type,
    rc.rig_status,

    SUM(f.rig_count) AS rig_count,

    COUNT(DISTINCT c.country_key)
        AS country_count

FROM fact_rig_count AS f

INNER JOIN dim_time AS t
    ON t.time_key = f.time_key

INNER JOIN dim_country AS c
    ON c.country_key = f.country_key

INNER JOIN dim_rig_classification AS rc
    ON rc.rig_classification_key =
       f.rig_classification_key

GROUP BY
    t.date,
    c.region,
    rc.drilling_target,
    rc.location_type,
    rc.rig_status;
"""


CREATE_LATEST_RIG_COUNT_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_latest_rig_count AS
WITH ranked_rig_counts AS
(
    SELECT
        f.rig_count_key,

        t.timestamp,
        t.date,

        c.country_key,
        c.country_name,
        c.region,

        rc.rig_classification_key,
        rc.drilling_target,
        rc.location_type,
        rc.rig_status,

        f.rig_count,
        f.source,
        f.source_file,
        f.source_ingestion_time,
        f.warehouse_loaded_at,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                c.country_key,
                rc.rig_classification_key,
                f.source

            ORDER BY
                t.timestamp DESC,
                f.warehouse_loaded_at DESC
        ) AS row_number

    FROM fact_rig_count AS f

    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key

    INNER JOIN dim_country AS c
        ON c.country_key = f.country_key

    INNER JOIN dim_rig_classification AS rc
        ON rc.rig_classification_key =
           f.rig_classification_key
)

SELECT
    rig_count_key,
    timestamp,
    date,
    country_key,
    country_name,
    region,
    rig_classification_key,
    drilling_target,
    location_type,
    rig_status,
    rig_count,
    source,
    source_file,
    source_ingestion_time,
    warehouse_loaded_at

FROM ranked_rig_counts

WHERE row_number = 1;
"""


CREATE_RIG_COUNT_MONTHLY_CHANGE_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_rig_count_monthly_change AS
WITH monthly_counts AS
(
    SELECT
        t.date,

        c.country_key,
        c.country_name,
        c.region,

        rc.rig_classification_key,
        rc.drilling_target,
        rc.location_type,
        rc.rig_status,

        SUM(f.rig_count) AS rig_count

    FROM fact_rig_count AS f

    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key

    INNER JOIN dim_country AS c
        ON c.country_key = f.country_key

    INNER JOIN dim_rig_classification AS rc
        ON rc.rig_classification_key =
           f.rig_classification_key

    GROUP BY
        t.date,
        c.country_key,
        c.country_name,
        c.region,
        rc.rig_classification_key,
        rc.drilling_target,
        rc.location_type,
        rc.rig_status
),

with_previous AS
(
    SELECT
        *,

        LAG(rig_count) OVER
        (
            PARTITION BY
                country_key,
                rig_classification_key

            ORDER BY date
        ) AS previous_month_rig_count

    FROM monthly_counts
)

SELECT
    date,
    country_key,
    country_name,
    region,
    rig_classification_key,
    drilling_target,
    location_type,
    rig_status,
    rig_count,
    previous_month_rig_count,

    rig_count
        - previous_month_rig_count
        AS monthly_change,

    CASE
        WHEN previous_month_rig_count IS NULL
            THEN NULL

        WHEN previous_month_rig_count = 0
            THEN NULL

        ELSE ROUND(
            (
                (
                    rig_count
                    - previous_month_rig_count
                )
                / previous_month_rig_count
            ) * 100,
            2
        )
    END AS monthly_change_percent

FROM with_previous;
"""


def build_rig_views() -> None:
    logger.info(
        "Creating rig-count analytical views"
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(
                CREATE_RIG_COUNT_HISTORY_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_RIG_COUNT_COUNTRY_MONTHLY_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_RIG_COUNT_REGION_MONTHLY_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_LATEST_RIG_COUNT_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_RIG_COUNT_MONTHLY_CHANGE_VIEW_SQL
            )
        )

    logger.success(
        "Rig-count analytical views created successfully"
    )


def main() -> None:
    build_rig_views()


if __name__ == "__main__":
    main()