from loguru import logger

from src.warehouse.create_rig_dimensions import (
    create_rig_dimensions,
)
from src.warehouse.create_rig_facts import (
    create_rig_facts,
)
from src.warehouse.load_rig_dimensions import (
    load_rig_dimensions,
)
from src.warehouse.load_rig_facts import (
    load_rig_facts,
)
from src.warehouse.build_rig_views import (
    build_rig_views,
)


def run_rig_warehouse_pipeline() -> None:
    logger.info(
        "Starting rig-count warehouse pipeline"
    )

    create_rig_dimensions()

    create_rig_facts()

    load_rig_dimensions()

    load_rig_facts()

    build_rig_views()

    logger.success(
        "Rig-count warehouse pipeline completed"
    )


def main() -> None:
    run_rig_warehouse_pipeline()


if __name__ == "__main__":
    main()