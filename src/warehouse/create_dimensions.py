from sqlalchemy import text
from loguru import logger

from src.config.database import get_engine


CREATE_DIM_ENERGY_PRODUCT = """
CREATE TABLE IF NOT EXISTS dim_energy_product
(
    product_key SERIAL PRIMARY KEY,

    product_code VARCHAR(50) NOT NULL UNIQUE,

    product_name VARCHAR(150) NOT NULL,

    commodity_type VARCHAR(50) NOT NULL,

    default_unit VARCHAR(50),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def create_dimensions() -> None:
    engine = get_engine()

    logger.info("Creating warehouse dimensions")

    with engine.begin() as connection:
        connection.execute(
            text(CREATE_DIM_ENERGY_PRODUCT)
        )

    logger.success(
        "Warehouse dimensions created successfully"
    )


def main() -> None:
    create_dimensions()


if __name__ == "__main__":
    main()