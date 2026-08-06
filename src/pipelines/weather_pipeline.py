from loguru import logger

from src.extract.extract_offshore_weather import (
    OffshoreWeatherExtractor,
)
from src.transform.transform_atmospheric_forecast import (
    AtmosphericForecastTransformer,
)
from src.transform.transform_marine_forecast import (
    MarineForecastTransformer,
)
from src.transform.build_operational_weather_risk import (
    build_operational_risk,
)
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


def run_weather_pipeline() -> None:
    """
    Run the complete offshore weather and marine pipeline.

    Execution order:
    1. Create or migrate dimensions.
    2. Create fact tables.
    3. Load asset and location dimensions.
    4. Extract atmospheric and marine forecasts.
    5. Transform Bronze JSON into Silver Parquet.
    6. Calculate operational weather risk.
    7. Load forecast and risk facts.
    8. Build analytical views.
    """

    logger.info(
        "Starting complete offshore weather pipeline"
    )

    logger.info(
        "Step 1/8 - Creating weather dimensions"
    )
    create_weather_dimensions()

    logger.info(
        "Step 2/8 - Creating weather fact tables"
    )
    create_weather_facts()

    logger.info(
        "Step 3/8 - Loading weather dimensions"
    )
    load_weather_dimensions()

    logger.info(
        "Step 4/8 - Extracting atmospheric and marine forecasts"
    )
    extractor = OffshoreWeatherExtractor()
    bronze_files = extractor.execute()

    logger.info(
        "Atmospheric Bronze file: {}",
        bronze_files["atmospheric"],
    )

    logger.info(
        "Marine Bronze file: {}",
        bronze_files["marine"],
    )

    logger.info(
        "Step 5/8 - Transforming atmospheric forecast"
    )
    atmospheric_transformer = (
        AtmosphericForecastTransformer()
    )
    atmospheric_file = (
        atmospheric_transformer.execute()
    )

    logger.info(
        "Atmospheric Silver file: {}",
        atmospheric_file,
    )

    logger.info(
        "Step 6/8 - Transforming marine forecast"
    )
    marine_transformer = (
        MarineForecastTransformer()
    )
    marine_file = marine_transformer.execute()

    logger.info(
        "Marine Silver file: {}",
        marine_file,
    )

    logger.info(
        "Step 7/8 - Building operational weather risk"
    )
    risk_file = build_operational_risk()

    logger.info(
        "Operational risk Silver file: {}",
        risk_file,
    )

    logger.info(
        "Loading weather and marine facts"
    )
    load_results = load_weather_facts()

    logger.info(
        "Atmospheric fact rows processed: {}",
        load_results["atmospheric"],
    )

    logger.info(
        "Marine fact rows processed: {}",
        load_results["marine"],
    )

    logger.info(
        "Operational risk rows processed: {}",
        load_results["risk"],
    )

    logger.info(
        "Step 8/8 - Building analytical views"
    )
    build_weather_views()

    logger.success(
        "Complete offshore weather pipeline finished successfully"
    )


def main() -> None:
    try:
        run_weather_pipeline()

    except Exception:
        logger.exception(
            "Offshore weather pipeline failed"
        )
        raise


if __name__ == "__main__":
    main()