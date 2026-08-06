from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_OIL_PRICE_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_oil_price_history AS
SELECT
    f.oil_price_key,

    t.time_key,
    t.timestamp,
    t.date,
    t.hour,
    t.month,
    t.season,

    p.product_key,
    p.product_code,
    p.product_name,
    p.commodity_type,
    p.default_unit,

    f.price_usd,
    f.unit,
    f.source,
    f.series,
    f.source_timestamp,
    f.ingestion_time

FROM fact_oil_price AS f

INNER JOIN dim_time AS t
    ON t.time_key = f.time_key

INNER JOIN dim_energy_product AS p
    ON p.product_key = f.product_key;
"""


CREATE_DAILY_SUMMARY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_daily_oil_price_summary AS
SELECT
    t.date,

    p.product_code,
    p.product_name,
    p.commodity_type,

    f.unit,
    f.source,
    f.series,

    COUNT(*) AS observation_count,

    MIN(f.price_usd) AS minimum_price,
    MAX(f.price_usd) AS maximum_price,
    AVG(f.price_usd) AS average_price,

    MIN(f.source_timestamp) AS first_observation,
    MAX(f.source_timestamp) AS last_observation

FROM fact_oil_price AS f

INNER JOIN dim_time AS t
    ON t.time_key = f.time_key

INNER JOIN dim_energy_product AS p
    ON p.product_key = f.product_key

GROUP BY
    t.date,
    p.product_code,
    p.product_name,
    p.commodity_type,
    f.unit,
    f.source,
    f.series;
"""


CREATE_LATEST_PRICE_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_latest_oil_price AS
WITH ranked_prices AS
(
    SELECT
        f.oil_price_key,

        t.timestamp,
        t.date,

        p.product_key,
        p.product_code,
        p.product_name,
        p.commodity_type,

        f.price_usd,
        f.unit,
        f.source,
        f.series,
        f.source_timestamp,
        f.ingestion_time,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                p.product_key,
                f.series

            ORDER BY
                t.timestamp DESC,
                f.ingestion_time DESC
        ) AS row_number

    FROM fact_oil_price AS f

    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key

    INNER JOIN dim_energy_product AS p
        ON p.product_key = f.product_key
)

SELECT
    oil_price_key,
    timestamp,
    date,
    product_key,
    product_code,
    product_name,
    commodity_type,
    price_usd,
    unit,
    source,
    series,
    source_timestamp,
    ingestion_time

FROM ranked_prices

WHERE row_number = 1;
"""


def build_views() -> None:
    logger.info(
        "Creating oil-price analytical views"
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(CREATE_OIL_PRICE_VIEW_SQL)
        )

        connection.execute(
            text(CREATE_DAILY_SUMMARY_VIEW_SQL)
        )

        connection.execute(
            text(CREATE_LATEST_PRICE_VIEW_SQL)
        )

    logger.success(
        "Oil-price analytical views created successfully"
    )


def main() -> None:
    build_views()


if __name__ == "__main__":
    main()