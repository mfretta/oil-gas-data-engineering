from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_OPERATIONAL_FORECAST_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_offshore_operational_forecast AS
SELECT
    a.asset_id,
    a.asset_name,
    a.asset_type,

    l.location_name,
    l.country,
    l.latitude,
    l.longitude,

    w.forecast_reference_time,
    w.forecast_valid_time,
    w.forecast_horizon_hours,

    w.temperature_c,
    w.relative_humidity_pct,
    w.pressure_hpa,
    w.precipitation_mm,
    w.wind_speed_kmh,
    w.wind_direction_deg,
    w.wind_gust_kmh,
    w.visibility_m,

    m.wave_height_m,
    m.wave_direction_deg,
    m.wave_period_s,
    m.swell_wave_height_m,
    m.swell_wave_direction_deg,
    m.swell_wave_period_s,
    m.sea_surface_temperature_c,
    m.ocean_current_velocity_kmh,
    m.ocean_current_direction_deg,

    r.wind_risk_level,
    r.gust_risk_level,
    r.wave_risk_level,
    r.visibility_risk_level,
    r.overall_risk_level,
    r.operation_recommendation,
    r.limiting_parameter

FROM fact_weather_forecast AS w

INNER JOIN dim_asset AS a
    ON a.asset_key = w.asset_key

INNER JOIN dim_location AS l
    ON l.location_key = a.location_key

LEFT JOIN fact_marine_forecast AS m
    ON m.asset_key = w.asset_key
   AND m.forecast_reference_time =
       w.forecast_reference_time
   AND m.forecast_valid_time =
       w.forecast_valid_time

LEFT JOIN fact_operational_weather_risk AS r
    ON r.asset_key = w.asset_key
   AND r.forecast_reference_time =
       w.forecast_reference_time
   AND r.forecast_valid_time =
       w.forecast_valid_time;
"""


CREATE_LATEST_OPERATIONAL_FORECAST_SQL = """
CREATE OR REPLACE VIEW vw_latest_offshore_forecast AS
WITH latest_run AS
(
    SELECT
        asset_id,
        MAX(forecast_reference_time)
            AS latest_reference_time
    FROM vw_offshore_operational_forecast
    GROUP BY asset_id
)

SELECT forecast.*
FROM vw_offshore_operational_forecast
    AS forecast

INNER JOIN latest_run
    ON latest_run.asset_id =
       forecast.asset_id
   AND latest_run.latest_reference_time =
       forecast.forecast_reference_time;
"""


CREATE_SAFE_WINDOW_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_offshore_safe_windows AS
SELECT
    asset_id,
    asset_name,
    forecast_valid_time,
    wind_speed_kmh,
    wind_gust_kmh,
    wave_height_m,
    visibility_m,
    overall_risk_level,
    operation_recommendation

FROM vw_latest_offshore_forecast

WHERE overall_risk_level = 'GREEN';
"""


CREATE_RISK_SUMMARY_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_offshore_risk_summary AS
SELECT
    asset_id,
    asset_name,
    DATE(forecast_valid_time)
        AS forecast_date,

    COUNT(*) AS forecast_hours,

    COUNT(*) FILTER
    (
        WHERE overall_risk_level = 'GREEN'
    ) AS green_hours,

    COUNT(*) FILTER
    (
        WHERE overall_risk_level = 'AMBER'
    ) AS amber_hours,

    COUNT(*) FILTER
    (
        WHERE overall_risk_level = 'RED'
    ) AS red_hours,

    MAX(wind_gust_kmh)
        AS maximum_wind_gust_kmh,

    MAX(wave_height_m)
        AS maximum_wave_height_m,

    MIN(visibility_m)
        AS minimum_visibility_m

FROM vw_latest_offshore_forecast

GROUP BY
    asset_id,
    asset_name,
    DATE(forecast_valid_time);
"""


def build_weather_views() -> None:
    logger.info(
        "Creating operational weather views"
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(
                CREATE_OPERATIONAL_FORECAST_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_LATEST_OPERATIONAL_FORECAST_SQL
            )
        )

        connection.execute(
            text(
                CREATE_SAFE_WINDOW_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_RISK_SUMMARY_VIEW_SQL
            )
        )

    logger.success(
        "Operational weather views created successfully"
    )


def main() -> None:
    build_weather_views()


if __name__ == "__main__":
    main()