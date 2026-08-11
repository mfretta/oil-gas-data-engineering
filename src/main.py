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
from src.warehouse.pipeline_observability import (
    start_pipeline_run,
    finish_pipeline_run_success,
    finish_pipeline_run_failed,
    save_quality_results,
)


def run_complete_pipeline():
    """
    Run the complete Oil & Gas Data Engineering pipeline.

    Returns
    -------
    list
        Warehouse data-quality validation results.
    """

    logger.info("=" * 70)

    logger.info(
        "Starting Oil & Gas Data Engineering pipeline"
    )

    logger.info("=" * 70)

    # ======================================================
    # STAGE 1 - WEATHER
    # ======================================================

    logger.info(
        "Stage 1/4 - Running offshore weather pipeline"
    )

    run_weather_pipeline()

    logger.success(
        "Stage 1/4 completed - Weather pipeline"
    )

    # ======================================================
    # STAGE 2 - RIG COUNT
    # ======================================================

    logger.info(
        "Stage 2/4 - Running rig-count warehouse pipeline"
    )

    run_rig_warehouse_pipeline()

    logger.success(
        "Stage 2/4 completed - Rig-count pipeline"
    )

    # ======================================================
    # STAGE 3 - ANALYTICAL VIEWS
    # ======================================================

    logger.info(
        "Stage 3/4 - Building integrated analytical views"
    )

    build_integrated_views()

    logger.success(
        "Stage 3/4 completed - Integrated views"
    )

    # ======================================================
    # STAGE 4 - DATA QUALITY
    # ======================================================

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

    # ======================================================
    # SUCCESS
    # ======================================================

    logger.info("=" * 70)

    logger.success(
        "Complete Oil & Gas Data Engineering pipeline "
        "finished successfully"
    )

    logger.info("=" * 70)

    return validation_results


def main() -> None:
    pipeline_run_key = start_pipeline_run(
        "oil-gas-data-engineering"
    )

    try:
        validation_results = (
            run_complete_pipeline()
        )

        save_quality_results(
            pipeline_run_key,
            validation_results,
        )

        finish_pipeline_run_success(
            pipeline_run_key
        )

        logger.success(
            "Pipeline observability records persisted "
            "successfully | run_key={}",
            pipeline_run_key,
        )

    except Exception as error:
        finish_pipeline_run_failed(
            pipeline_run_key,
            str(error),
        )

        logger.exception(
            "Complete Oil & Gas pipeline failed"
        )

        raise


if __name__ == "__main__":
    main()