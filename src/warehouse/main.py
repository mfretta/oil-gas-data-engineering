from loguru import logger

from src.warehouse.create_dimensions import (
    create_dimensions,
)
from src.warehouse.create_facts import (
    create_facts,
)
from src.warehouse.load_dimensions import (
    load_dimensions,
)
from src.warehouse.load_facts import (
    load_facts,
)
from src.warehouse.build_views import (
    build_views,
)


def run_warehouse_pipeline() -> None:
    logger.info(
        "Starting oil-price warehouse pipeline"
    )

    create_dimensions()

    create_facts()

    load_dimensions()

    load_facts()

    build_views()

    logger.success(
        "Oil-price warehouse pipeline completed"
    )


def main() -> None:
    run_warehouse_pipeline()


if __name__ == "__main__":
    main()