from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


# ============================================================
# DAILY ENERGY PRICE VIEW
# ============================================================

CREATE_DAILY_OIL_PRICE_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_daily_oil_price AS

SELECT
    t.date,

    ep.product_key,
    ep.product_code,
    ep.product_name AS product,
    ep.commodity_type,

    f.unit,
    f.source,

    AVG(f.price_usd) AS average_price_usd,

    MIN(f.price_usd) AS minimum_price_usd,

    MAX(f.price_usd) AS maximum_price_usd,

    COUNT(*) AS observations

FROM fact_oil_price AS f

INNER JOIN dim_time AS t
    ON t.time_key = f.time_key

INNER JOIN dim_energy_product AS ep
    ON ep.product_key = f.product_key

GROUP BY
    t.date,
    ep.product_key,
    ep.product_code,
    ep.product_name,
    ep.commodity_type,
    f.unit,
    f.source;
"""


# ============================================================
# LATEST ENERGY PRICE VIEW
# ============================================================

CREATE_LATEST_OIL_PRICE_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_latest_oil_price AS

WITH ranked_prices AS
(
    SELECT
        t.date,

        ep.product_key,
        ep.product_code,
        ep.product_name AS product,
        ep.commodity_type,

        f.price_usd,
        f.unit,
        f.source,

        ROW_NUMBER() OVER
        (
            PARTITION BY ep.product_key
            ORDER BY t.date DESC
        ) AS row_num

    FROM fact_oil_price AS f

    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key

    INNER JOIN dim_energy_product AS ep
        ON ep.product_key = f.product_key
)

SELECT
    date,
    product_key,
    product_code,
    product,
    commodity_type,
    price_usd,
    unit,
    source

FROM ranked_prices

WHERE row_num = 1;
"""


# ============================================================
# ENERGY PRICE SUMMARY VIEW
# ============================================================

CREATE_ENERGY_PRICE_SUMMARY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_energy_price_summary AS

SELECT
    ep.product_key,
    ep.product_code,
    ep.product_name AS product,
    ep.commodity_type,

    MIN(t.date) AS first_observation_date,

    MAX(t.date) AS latest_observation_date,

    COUNT(*) AS total_observations,

    ROUND(
        AVG(f.price_usd),
        4
    ) AS average_price_usd,

    MIN(f.price_usd) AS minimum_price_usd,

    MAX(f.price_usd) AS maximum_price_usd,

    MAX(f.unit) AS unit,

    MAX(f.source) AS source

FROM fact_oil_price AS f

INNER JOIN dim_time AS t
    ON t.time_key = f.time_key

INNER JOIN dim_energy_product AS ep
    ON ep.product_key = f.product_key

GROUP BY
    ep.product_key,
    ep.product_code,
    ep.product_name,
    ep.commodity_type;
"""


# ============================================================
# BUILD VIEWS
# ============================================================

def build_energy_views() -> None:
    """
    Recreate analytical views for energy-price intelligence.
    """

    logger.info(
        "Creating energy analytical views"
    )

    engine = get_engine()

    with engine.begin() as connection:

        # ----------------------------------------------------
        # DROP OLD VIEWS
        # ----------------------------------------------------

        logger.info(
            "Dropping existing energy views"
        )

        connection.execute(
            text(
                """
                DROP VIEW IF EXISTS
                    vw_energy_price_summary
                CASCADE;
                """
            )
        )

        connection.execute(
            text(
                """
                DROP VIEW IF EXISTS
                    vw_latest_oil_price
                CASCADE;
                """
            )
        )

        connection.execute(
            text(
                """
                DROP VIEW IF EXISTS
                    vw_daily_oil_price
                CASCADE;
                """
            )
        )

        # ----------------------------------------------------
        # CREATE DAILY VIEW
        # ----------------------------------------------------

        logger.info(
            "Creating vw_daily_oil_price"
        )

        connection.execute(
            text(
                CREATE_DAILY_OIL_PRICE_VIEW_SQL
            )
        )

        # ----------------------------------------------------
        # CREATE LATEST VIEW
        # ----------------------------------------------------

        logger.info(
            "Creating vw_latest_oil_price"
        )

        connection.execute(
            text(
                CREATE_LATEST_OIL_PRICE_VIEW_SQL
            )
        )

        # ----------------------------------------------------
        # CREATE SUMMARY VIEW
        # ----------------------------------------------------

        logger.info(
            "Creating vw_energy_price_summary"
        )

        connection.execute(
            text(
                CREATE_ENERGY_PRICE_SUMMARY_VIEW_SQL
            )
        )

    logger.success(
        "Energy analytical views created successfully"
    )


def main() -> None:
    build_energy_views()


if __name__ == "__main__":
    main()