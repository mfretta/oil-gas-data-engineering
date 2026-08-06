from loguru import logger

from src.pipelines.weather_pipeline import (
    run_weather_pipeline,
)
from src.warehouse.rig_pipeline import (
    run_rig_warehouse_pipeline,
)
from src.warehouse.build_integrated_views import (
    build_integrated_views,
)
from src.quality.validate_warehouse import (
    validate_warehouse,
)


def run_complete_pipeline() -> None:
    """
    Run the complete Oil & Gas Data Engineering project.

    Execution order:
    1. Offshore weather and marine pipeline
    2. Baker Hughes rig-count warehouse
    3. Integrated analytical views
    4. Warehouse data-quality validation
    """

    logger.info(
        "=" * 70
    )

    logger.info(
        "Starting Oil & Gas Data Engineering pipeline"
    )

    logger.info(
        "=" * 70
    )

    logger.info(
        "Stage 1/4 - Running offshore weather pipeline"
    )

    run_weather_pipeline()

    logger.success(
        "Stage 1/4 completed - Weather pipeline"
    )

    logger.info(
        "Stage 2/4 - Running rig-count warehouse pipeline"
    )

    run_rig_warehouse_pipeline()

    logger.success(
        "Stage 2/4 completed - Rig-count pipeline"
    )

    logger.info(
        "Stage 3/4 - Building integrated analytical views"
    )

    build_integrated_views()

    logger.success(
        "Stage 3/4 completed - Integrated views"
    )

    logger.info(
        "Stage 4/4 - Running warehouse quality validation"
    )

    validation_results = validate_warehouse()

    failed_checks = [
        result
        for result in validation_results
        if not result.passed
    ]

    if failed_checks:
        failed_names = [
            result.name
            for result in failed_checks
        ]

        raise RuntimeError(
            "Warehouse validation failed. "
            "Failed checks: "
            + ", ".join(failed_names)
        )

    logger.success(
        "Stage 4/4 completed - Quality validation"
    )

    logger.info(
        "=" * 70
    )

    logger.success(
        "Complete Oil & Gas Data Engineering pipeline "
        "finished successfully"
    )

    logger.info(
        "=" * 70
    )


def main() -> None:
    try:
        run_complete_pipeline()

    except Exception:
        logger.exception(
            "Complete Oil & Gas pipeline failed"
        )

        raise


if __name__ == "__main__":
    main()