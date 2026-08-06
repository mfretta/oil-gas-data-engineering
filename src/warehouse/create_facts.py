from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_FACT_OIL_PRICE_SQL = """
CREATE TABLE IF NOT EXISTS fact_oil_price
(
    oil_price_key BIGSERIAL PRIMARY KEY,

    time_key INTEGER NOT NULL,

    product_key INTEGER NOT NULL,

    price_usd NUMERIC(12, 4) NOT NULL,

    unit VARCHAR(50) NOT NULL,

    source VARCHAR(100) NOT NULL,

    series VARCHAR(150) NOT NULL,

    source_timestamp TIMESTAMP NOT NULL,

    ingestion_time TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_oil_price_time
        FOREIGN KEY (time_key)
        REFERENCES dim_time(time_key),

    CONSTRAINT fk_oil_price_product
        FOREIGN KEY (product_key)
        REFERENCES dim_energy_product(product_key),

    CONSTRAINT uq_oil_price_observation
        UNIQUE
        (
            time_key,
            product_key,
            source,
            series
        ),

    CONSTRAINT chk_oil_price_non_negative
        CHECK (price_usd >= 0)
);
"""


CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_fact_oil_price_time_key
    ON fact_oil_price(time_key);

CREATE INDEX IF NOT EXISTS idx_fact_oil_price_product_key
    ON fact_oil_price(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_oil_price_series
    ON fact_oil_price(series);

CREATE INDEX IF NOT EXISTS idx_fact_oil_price_timestamp
    ON fact_oil_price(source_timestamp);

CREATE INDEX IF NOT EXISTS idx_fact_oil_price_product_time
    ON fact_oil_price(product_key, time_key);
"""


def create_facts() -> None:
    logger.info("Creating fact_oil_price")

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(CREATE_FACT_OIL_PRICE_SQL)
        )

        connection.execute(
            text(CREATE_INDEXES_SQL)
        )

    logger.success(
        "fact_oil_price and indexes are ready"
    )


def main() -> None:
    create_facts()


if __name__ == "__main__":
    main()