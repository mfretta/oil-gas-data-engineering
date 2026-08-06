from dataclasses import dataclass
from typing import Any

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from src.config.database import get_engine


@dataclass
class CheckResult:
    name: str
    passed: bool
    value: Any
    expectation: str
    details: str = ""


REQUIRED_TABLES = {
    "dim_location",
    "dim_time",
    "dim_asset",
    "dim_country",
    "dim_rig_classification",
    "dim_energy_product",
    "fact_weather_forecast",
    "fact_marine_forecast",
    "fact_operational_weather_risk",
    "fact_rig_count",
    "fact_oil_price",
}


REQUIRED_VIEWS = {
    "vw_latest_offshore_forecast",
    "vw_offshore_operational_forecast",
    "vw_offshore_risk_summary",
    "vw_offshore_safe_windows",
    "vw_executive_energy_operations",
    "vw_asset_operational_kpis",
    "vw_next_weather_critical_event",
}


def scalar(
    connection: Connection,
    query: str,
) -> Any:
    return connection.execute(
        text(query)
    ).scalar()


def check_required_objects(
    connection: Connection,
) -> list[CheckResult]:
    inspector = inspect(connection)

    existing_tables = set(
        inspector.get_table_names(
            schema="public"
        )
    )

    existing_views = set(
        inspector.get_view_names(
            schema="public"
        )
    )

    missing_tables = sorted(
        REQUIRED_TABLES - existing_tables
    )

    missing_views = sorted(
        REQUIRED_VIEWS - existing_views
    )

    return [
        CheckResult(
            name="Required tables",
            passed=not missing_tables,
            value=len(
                REQUIRED_TABLES & existing_tables
            ),
            expectation=(
                f"{len(REQUIRED_TABLES)} required tables"
            ),
            details=(
                "Missing: "
                + ", ".join(missing_tables)
                if missing_tables
                else "All required tables exist."
            ),
        ),
        CheckResult(
            name="Required analytical views",
            passed=not missing_views,
            value=len(
                REQUIRED_VIEWS & existing_views
            ),
            expectation=(
                f"{len(REQUIRED_VIEWS)} required views"
            ),
            details=(
                "Missing: "
                + ", ".join(missing_views)
                if missing_views
                else "All required views exist."
            ),
        ),
    ]


def check_fact_row_counts(
    connection: Connection,
) -> list[CheckResult]:
    tables = [
        "fact_weather_forecast",
        "fact_marine_forecast",
        "fact_operational_weather_risk",
        "fact_rig_count",
        "fact_oil_price",
    ]

    results = []

    for table_name in tables:
        row_count = scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM {table_name};
            """,
        )

        results.append(
            CheckResult(
                name=f"{table_name} row count",
                passed=row_count > 0,
                value=row_count,
                expectation="Greater than zero",
                details=(
                    "Dataset contains records."
                    if row_count > 0
                    else "Dataset is empty."
                ),
            )
        )

    return results


def check_weather_alignment(
    connection: Connection,
) -> list[CheckResult]:
    atmospheric_rows = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_weather_forecast;
        """,
    )

    marine_rows = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_marine_forecast;
        """,
    )

    risk_rows = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_operational_weather_risk;
        """,
    )

    latest_atmospheric_rows = scalar(
        connection,
        """
        WITH latest_run AS
        (
            SELECT MAX(
                forecast_reference_time
            ) AS reference_time
            FROM fact_weather_forecast
        )
        SELECT COUNT(*)
        FROM fact_weather_forecast AS f
        JOIN latest_run AS latest
          ON latest.reference_time =
             f.forecast_reference_time;
        """,
    )

    latest_marine_rows = scalar(
        connection,
        """
        WITH latest_run AS
        (
            SELECT MAX(
                forecast_reference_time
            ) AS reference_time
            FROM fact_marine_forecast
        )
        SELECT COUNT(*)
        FROM fact_marine_forecast AS f
        JOIN latest_run AS latest
          ON latest.reference_time =
             f.forecast_reference_time;
        """,
    )

    latest_risk_rows = scalar(
        connection,
        """
        WITH latest_run AS
        (
            SELECT MAX(
                forecast_reference_time
            ) AS reference_time
            FROM fact_operational_weather_risk
        )
        SELECT COUNT(*)
        FROM fact_operational_weather_risk AS f
        JOIN latest_run AS latest
          ON latest.reference_time =
             f.forecast_reference_time;
        """,
    )

    return [
        CheckResult(
            name="Historical weather table alignment",
            passed=(
                atmospheric_rows
                == marine_rows
                == risk_rows
            ),
            value={
                "atmospheric": atmospheric_rows,
                "marine": marine_rows,
                "risk": risk_rows,
            },
            expectation=(
                "Atmospheric, marine, and risk "
                "tables have equal row counts"
            ),
        ),
        CheckResult(
            name="Latest weather-run alignment",
            passed=(
                latest_atmospheric_rows
                == latest_marine_rows
                == latest_risk_rows
            ),
            value={
                "atmospheric":
                    latest_atmospheric_rows,
                "marine":
                    latest_marine_rows,
                "risk":
                    latest_risk_rows,
            },
            expectation=(
                "Latest forecast run has equal "
                "row counts across all weather facts"
            ),
        ),
    ]


def check_weather_duplicates(
    connection: Connection,
) -> list[CheckResult]:
    checks = {
        "Atmospheric duplicate grain": """
            SELECT COUNT(*)
            FROM
            (
                SELECT
                    asset_key,
                    forecast_reference_time,
                    forecast_valid_time,
                    source,
                    COUNT(*) AS records
                FROM fact_weather_forecast
                GROUP BY
                    asset_key,
                    forecast_reference_time,
                    forecast_valid_time,
                    source
                HAVING COUNT(*) > 1
            ) AS duplicates;
        """,
        "Marine duplicate grain": """
            SELECT COUNT(*)
            FROM
            (
                SELECT
                    asset_key,
                    forecast_reference_time,
                    forecast_valid_time,
                    source,
                    COUNT(*) AS records
                FROM fact_marine_forecast
                GROUP BY
                    asset_key,
                    forecast_reference_time,
                    forecast_valid_time,
                    source
                HAVING COUNT(*) > 1
            ) AS duplicates;
        """,
        "Risk duplicate grain": """
            SELECT COUNT(*)
            FROM
            (
                SELECT
                    asset_key,
                    forecast_reference_time,
                    forecast_valid_time,
                    source,
                    COUNT(*) AS records
                FROM fact_operational_weather_risk
                GROUP BY
                    asset_key,
                    forecast_reference_time,
                    forecast_valid_time,
                    source
                HAVING COUNT(*) > 1
            ) AS duplicates;
        """,
    }

    results = []

    for check_name, query in checks.items():
        duplicate_groups = scalar(
            connection,
            query,
        )

        results.append(
            CheckResult(
                name=check_name,
                passed=duplicate_groups == 0,
                value=duplicate_groups,
                expectation="Zero duplicate groups",
            )
        )

    return results


def check_weather_dimensions(
    connection: Connection,
) -> list[CheckResult]:
    orphan_weather_assets = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_weather_forecast AS f
        LEFT JOIN dim_asset AS a
          ON a.asset_key = f.asset_key
        WHERE a.asset_key IS NULL;
        """,
    )

    orphan_marine_assets = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_marine_forecast AS f
        LEFT JOIN dim_asset AS a
          ON a.asset_key = f.asset_key
        WHERE a.asset_key IS NULL;
        """,
    )

    assets_without_locations = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM dim_asset AS a
        LEFT JOIN dim_location AS l
          ON l.location_key = a.location_key
        WHERE a.is_active = TRUE
          AND l.location_key IS NULL;
        """,
    )

    return [
        CheckResult(
            name="Weather asset references",
            passed=orphan_weather_assets == 0,
            value=orphan_weather_assets,
            expectation="Zero orphan asset keys",
        ),
        CheckResult(
            name="Marine asset references",
            passed=orphan_marine_assets == 0,
            value=orphan_marine_assets,
            expectation="Zero orphan asset keys",
        ),
        CheckResult(
            name="Active asset locations",
            passed=assets_without_locations == 0,
            value=assets_without_locations,
            expectation=(
                "Every active asset has a location"
            ),
        ),
    ]


def check_weather_values(
    connection: Connection,
) -> list[CheckResult]:
    invalid_humidity = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_weather_forecast
        WHERE relative_humidity_pct
              NOT BETWEEN 0 AND 100;
        """,
    )

    invalid_wave_height = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_marine_forecast
        WHERE wave_height_m < 0;
        """,
    )

    invalid_visibility = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_weather_forecast
        WHERE visibility_m < 0;
        """,
    )

    invalid_risk_levels = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM fact_operational_weather_risk
        WHERE overall_risk_level NOT IN
        (
            'GREEN',
            'AMBER',
            'RED',
            'UNKNOWN'
        );
        """,
    )

    return [
        CheckResult(
            name="Relative humidity range",
            passed=invalid_humidity == 0,
            value=invalid_humidity,
            expectation=(
                "All values between 0 and 100"
            ),
        ),
        CheckResult(
            name="Wave-height range",
            passed=invalid_wave_height == 0,
            value=invalid_wave_height,
            expectation="No negative wave heights",
        ),
        CheckResult(
            name="Visibility range",
            passed=invalid_visibility == 0,
            value=invalid_visibility,
            expectation="No negative visibility",
        ),
        CheckResult(
            name="Operational risk categories",
            passed=invalid_risk_levels == 0,
            value=invalid_risk_levels,
            expectation=(
                "Only GREEN, AMBER, RED, or UNKNOWN"
            ),
        ),
    ]


def check_business_views(
    connection: Connection,
) -> list[CheckResult]:
    executive_rows = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM vw_executive_energy_operations;
        """,
    )

    asset_kpi_rows = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM vw_asset_operational_kpis;
        """,
    )

    latest_weather_rows = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM vw_latest_offshore_forecast;
        """,
    )

    active_assets = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM dim_asset
        WHERE is_active = TRUE;
        """,
    )

    return [
        CheckResult(
            name="Executive snapshot grain",
            passed=executive_rows == 1,
            value=executive_rows,
            expectation="Exactly one row",
        ),
        CheckResult(
            name="Asset KPI coverage",
            passed=asset_kpi_rows == active_assets,
            value={
                "view_rows": asset_kpi_rows,
                "active_assets": active_assets,
            },
            expectation=(
                "One KPI row per active asset"
            ),
        ),
        CheckResult(
            name="Latest offshore forecast",
            passed=latest_weather_rows > 0,
            value=latest_weather_rows,
            expectation="Greater than zero",
        ),
    ]


def print_results(
    results: list[CheckResult],
) -> None:
    print("\n" + "=" * 90)
    print("OIL & GAS DATA WAREHOUSE QUALITY REPORT")
    print("=" * 90)

    for result in results:
        status = "PASS" if result.passed else "FAIL"

        print(
            f"\n[{status}] {result.name}"
        )
        print(
            f"  Value:       {result.value}"
        )
        print(
            f"  Expectation: {result.expectation}"
        )

        if result.details:
            print(
                f"  Details:     {result.details}"
            )

    passed = sum(
        result.passed
        for result in results
    )

    failed = len(results) - passed

    print("\n" + "-" * 90)
    print(
        f"Checks passed: {passed}"
    )
    print(
        f"Checks failed: {failed}"
    )
    print(
        f"Total checks:  {len(results)}"
    )
    print("-" * 90)


def validate_warehouse() -> list[CheckResult]:
    logger.info(
        "Starting warehouse data-quality validation"
    )

    engine = get_engine()

    with engine.connect() as connection:
        results = []

        results.extend(
            check_required_objects(
                connection
            )
        )

        existing_tables = set(
            inspect(connection).get_table_names(
                schema="public"
            )
        )

        existing_views = set(
            inspect(connection).get_view_names(
                schema="public"
            )
        )

        if REQUIRED_TABLES.issubset(
            existing_tables
        ):
            results.extend(
                check_fact_row_counts(
                    connection
                )
            )

            results.extend(
                check_weather_alignment(
                    connection
                )
            )

            results.extend(
                check_weather_duplicates(
                    connection
                )
            )

            results.extend(
                check_weather_dimensions(
                    connection
                )
            )

            results.extend(
                check_weather_values(
                    connection
                )
            )

        if REQUIRED_VIEWS.issubset(
            existing_views
        ):
            results.extend(
                check_business_views(
                    connection
                )
            )

    print_results(results)

    failed_checks = [
        result
        for result in results
        if not result.passed
    ]

    if failed_checks:
        logger.error(
            "Warehouse validation failed: {} checks failed",
            len(failed_checks),
        )

    else:
        logger.success(
            "Warehouse validation completed successfully"
        )

    return results


def main() -> None:
    results = validate_warehouse()

    failed_checks = [
        result
        for result in results
        if not result.passed
    ]

    if failed_checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()