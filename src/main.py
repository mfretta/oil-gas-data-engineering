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

from src.warehouse.build_observability_views import (
    build_observability_views,
)

from src.warehouse.create_observability_tables import (
    create_observability_tables,
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

from src.warehouse.build_energy_views import (
    build_energy_views,
)
from src.warehouse.create_dimensions import create_dimensions
from src.warehouse.create_facts import create_facts
from src.warehouse.load_dimensions import load_dimensions
from src.warehouse.load_facts import load_facts
from src.warehouse.build_energy_views import build_energy_views


# ============================================================
# COMPLETE PIPELINE
# ============================================================

def run_complete_pipeline():
    """
    Run the complete Oil & Gas Data Engineering pipeline.

    Returns
    -------
    list
        Data-quality validation results.
    """

    logger.info("=" * 70)
    logger.info("Starting Oil & Gas Data Engineering pipeline")
    logger.info("=" * 70)

    # ========================================================
    # STAGE 1 - WEATHER
    # ========================================================

    logger.info(
        "Stage 1/5 - Running offshore weather pipeline"
    )

    run_weather_pipeline()

    logger.success(
        "Stage 1/5 completed - Weather pipeline"
    )

    # ========================================================
    # STAGE 2 - RIG COUNT
    # ========================================================

    logger.info(
        "Stage 2/5 - Running rig-count warehouse pipeline"
    )

    run_rig_warehouse_pipeline()

    logger.success(
        "Stage 2/5 completed - Rig-count pipeline"
    )

    # ========================================================
    # STAGE 3 - ENERGY PRICE
    # ========================================================

    logger.info(
        "Stage 3/5 - Running energy-price warehouse pipeline"
    )

    create_dimensions()
    create_facts()

    load_dimensions()

    fact_rows_loaded = load_facts()

    logger.info(
        "Energy-price fact rows loaded: {}",
        fact_rows_loaded,
    )

    build_energy_views()

    logger.success(
        "Stage 3/5 completed - Energy-price pipeline"
    )

    # ========================================================
    # STAGE 4 - INTEGRATED VIEWS
    # ========================================================

    logger.info(
        "Stage 4/5 - Building integrated analytical views"
    )

    build_integrated_views()

    logger.success(
        "Stage 4/5 completed - Integrated views"
    )

    # ========================================================
    # STAGE 5 - DATA QUALITY
    # ========================================================

    logger.info(
        "Stage 5/5 - Running warehouse quality validation"
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
        "Stage 5/5 completed - Quality validation"
    )

    logger.info("=" * 70)

    logger.success(
        "Complete Oil & Gas Data Engineering pipeline "
        "finished successfully"
    )

    logger.info("=" * 70)

    return validation_results


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def main() -> None:
    """
    Master orchestration entry point.

    Important:
    Observability tables are created before a pipeline-run
    record is inserted. This allows execution against a
    completely fresh PostgreSQL database, including Docker.
    """

    # --------------------------------------------------------
    # BOOTSTRAP OBSERVABILITY
    # --------------------------------------------------------

    logger.info(
        "Bootstrapping pipeline observability"
    )

    create_observability_tables()


    # --------------------------------------------------------
    # START PIPELINE RUN
    # --------------------------------------------------------

    pipeline_run_key = start_pipeline_run(
        "oil-gas-data-engineering"
    )


    try:

        # ----------------------------------------------------
        # EXECUTE PIPELINE
        # ----------------------------------------------------

        validation_results = (
            run_complete_pipeline()
        )


        # ----------------------------------------------------
        # PERSIST QUALITY RESULTS
        # ----------------------------------------------------

        save_quality_results(
            pipeline_run_key,
            validation_results,
        )


        # ----------------------------------------------------
        # MARK SUCCESS
        # ----------------------------------------------------

        finish_pipeline_run_success(
            pipeline_run_key
        )


        # ----------------------------------------------------
        # REFRESH OBSERVABILITY VIEWS
        # ----------------------------------------------------

        build_observability_views()


        logger.success(
            "Pipeline observability records persisted "
            "successfully | run_key={}",
            pipeline_run_key,
        )


    except Exception as error:

        # ----------------------------------------------------
        # MARK FAILED
        # ----------------------------------------------------

        finish_pipeline_run_failed(
            pipeline_run_key,
            str(error),
        )


        # ----------------------------------------------------
        # TRY TO REFRESH OBSERVABILITY VIEWS
        # ----------------------------------------------------

        try:

            build_observability_views()

        except Exception as view_error:

            logger.warning(
                "Could not rebuild observability views "
                "after pipeline failure: {}",
                view_error,
            )


        logger.exception(
            "Complete Oil & Gas pipeline failed"
        )

        raise


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()