from loguru import logger

from src.warehouse.create_weather_dimensions import (
    create_weather_dimensions,
)
from src.warehouse.create_weather_facts import (
    create_weather_facts,
)
from src.warehouse.load_weather_dimensions import (
    load_weather_dimensions,
)
from src.warehouse.load_weather_facts import (
    load_weather_facts,
)
from src.warehouse.build_weather_views import (
    build_weather_views,
)


def run_weather_warehouse_pipeline() -> None:
    logger.info(
        "Starting operational weather warehouse pipeline"
    )

    create_weather_dimensions()

    create_weather_facts()

    load_weather_dimensions()

    load_weather_facts()

    build_weather_views()

    logger.success(
        "Operational weather warehouse pipeline completed"
    )


def main() -> None:
    run_weather_warehouse_pipeline()


if __name__ == "__main__":
    main()