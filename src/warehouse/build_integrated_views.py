from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


CREATE_EXECUTIVE_SNAPSHOT_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_executive_energy_operations AS

WITH latest_rig_date AS
(
    SELECT
        MAX(t.date) AS latest_date
    FROM fact_rig_count AS f
    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key
),

latest_rig_summary AS
(
    SELECT
        t.date AS rig_count_date,
        SUM(f.rig_count) AS total_rig_count,
        COUNT(DISTINCT f.country_key)
            AS countries_reporting
    FROM fact_rig_count AS f
    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key
    INNER JOIN latest_rig_date AS d
        ON d.latest_date = t.date
    GROUP BY t.date
),

latest_price_date AS
(
    SELECT
        MAX(t.date) AS latest_date
    FROM fact_oil_price AS f
    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key
),

latest_price_summary AS
(
    SELECT
        t.date AS energy_price_date,
        AVG(f.price_usd) AS average_energy_price_usd,
        MIN(f.price_usd) AS minimum_energy_price_usd,
        MAX(f.price_usd) AS maximum_energy_price_usd,
        COUNT(*) AS energy_price_observations
    FROM fact_oil_price AS f
    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key
    INNER JOIN latest_price_date AS d
        ON d.latest_date = t.date
    GROUP BY t.date
),

latest_weather_run AS
(
    SELECT
        MAX(forecast_reference_time)
            AS latest_reference_time
    FROM fact_operational_weather_risk
),

weather_summary AS
(
    SELECT
        r.forecast_reference_time,
        MIN(r.forecast_valid_time)
            AS first_forecast_valid_time,
        MAX(r.forecast_valid_time)
            AS last_forecast_valid_time,

        COUNT(DISTINCT r.asset_key)
            AS monitored_assets,

        COUNT(*) AS forecast_hours,

        COUNT(*) FILTER
        (
            WHERE r.overall_risk_level = 'GREEN'
        ) AS green_hours,

        COUNT(*) FILTER
        (
            WHERE r.overall_risk_level = 'AMBER'
        ) AS amber_hours,

        COUNT(*) FILTER
        (
            WHERE r.overall_risk_level = 'RED'
        ) AS red_hours,

        COUNT(*) FILTER
        (
            WHERE r.overall_risk_level = 'UNKNOWN'
        ) AS unknown_hours

    FROM fact_operational_weather_risk AS r

    INNER JOIN latest_weather_run AS latest
        ON latest.latest_reference_time =
           r.forecast_reference_time

    GROUP BY
        r.forecast_reference_time
)

SELECT
    CURRENT_TIMESTAMP
        AS snapshot_generated_at,

    rig.rig_count_date,
    rig.total_rig_count,
    rig.countries_reporting,

    price.energy_price_date,
    price.average_energy_price_usd,
    price.minimum_energy_price_usd,
    price.maximum_energy_price_usd,
    price.energy_price_observations,

    weather.forecast_reference_time
        AS weather_forecast_reference_time,

    weather.first_forecast_valid_time,
    weather.last_forecast_valid_time,
    weather.monitored_assets,
    weather.forecast_hours,
    weather.green_hours,
    weather.amber_hours,
    weather.red_hours,
    weather.unknown_hours,

    ROUND(
        (
            weather.green_hours::NUMERIC
            / NULLIF(
                weather.forecast_hours,
                0
            )
        ) * 100,
        2
    ) AS green_hours_percent,

    ROUND(
        (
            weather.amber_hours::NUMERIC
            / NULLIF(
                weather.forecast_hours,
                0
            )
        ) * 100,
        2
    ) AS amber_hours_percent,

    ROUND(
        (
            weather.red_hours::NUMERIC
            / NULLIF(
                weather.forecast_hours,
                0
            )
        ) * 100,
        2
    ) AS red_hours_percent

FROM latest_rig_summary AS rig
CROSS JOIN latest_price_summary AS price
CROSS JOIN weather_summary AS weather;
"""


CREATE_ASSET_OPERATIONAL_KPI_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_asset_operational_kpis AS

WITH latest_run AS
(
    SELECT
        asset_id,
        MAX(forecast_reference_time)
            AS latest_reference_time
    FROM vw_offshore_operational_forecast
    GROUP BY asset_id
)

SELECT
    forecast.asset_id,
    forecast.asset_name,
    forecast.asset_type,
    forecast.location_name,
    forecast.country,

    forecast.forecast_reference_time,

    MIN(forecast.forecast_valid_time)
        AS first_forecast_valid_time,

    MAX(forecast.forecast_valid_time)
        AS last_forecast_valid_time,

    COUNT(*) AS forecast_hours,

    COUNT(*) FILTER
    (
        WHERE forecast.overall_risk_level = 'GREEN'
    ) AS green_hours,

    COUNT(*) FILTER
    (
        WHERE forecast.overall_risk_level = 'AMBER'
    ) AS amber_hours,

    COUNT(*) FILTER
    (
        WHERE forecast.overall_risk_level = 'RED'
    ) AS red_hours,

    COUNT(*) FILTER
    (
        WHERE forecast.overall_risk_level = 'UNKNOWN'
    ) AS unknown_hours,

    MAX(forecast.wind_speed_kmh)
        AS maximum_wind_speed_kmh,

    MAX(forecast.wind_gust_kmh)
        AS maximum_wind_gust_kmh,

    MAX(forecast.wave_height_m)
        AS maximum_wave_height_m,

    MIN(forecast.visibility_m)
        AS minimum_visibility_m,

    AVG(forecast.temperature_c)
        AS average_temperature_c,

    AVG(forecast.sea_surface_temperature_c)
        AS average_sea_surface_temperature_c,

    MIN(
        CASE
            WHEN forecast.overall_risk_level = 'RED'
            THEN forecast.forecast_valid_time
        END
    ) AS first_red_risk_time,

    MIN(
        CASE
            WHEN forecast.overall_risk_level = 'GREEN'
            THEN forecast.forecast_valid_time
        END
    ) AS first_green_window_time

FROM vw_offshore_operational_forecast AS forecast

INNER JOIN latest_run
    ON latest_run.asset_id =
       forecast.asset_id

   AND latest_run.latest_reference_time =
       forecast.forecast_reference_time

GROUP BY
    forecast.asset_id,
    forecast.asset_name,
    forecast.asset_type,
    forecast.location_name,
    forecast.country,
    forecast.forecast_reference_time;
"""


CREATE_NEXT_CRITICAL_EVENT_VIEW_SQL = """
CREATE OR REPLACE VIEW vw_next_weather_critical_event AS

WITH ranked_events AS
(
    SELECT
        asset_id,
        asset_name,
        asset_type,
        location_name,

        forecast_reference_time,
        forecast_valid_time,
        forecast_horizon_hours,

        wind_speed_kmh,
        wind_gust_kmh,
        wave_height_m,
        visibility_m,

        overall_risk_level,
        limiting_parameter,
        operation_recommendation,

        ROW_NUMBER() OVER
        (
            PARTITION BY asset_id

            ORDER BY
                forecast_valid_time
        ) AS event_rank

    FROM vw_latest_offshore_forecast

    WHERE overall_risk_level IN
    (
        'AMBER',
        'RED'
    )

    AND forecast_valid_time >=
        CURRENT_TIMESTAMP
)

SELECT
    asset_id,
    asset_name,
    asset_type,
    location_name,
    forecast_reference_time,
    forecast_valid_time,
    forecast_horizon_hours,
    wind_speed_kmh,
    wind_gust_kmh,
    wave_height_m,
    visibility_m,
    overall_risk_level,
    limiting_parameter,
    operation_recommendation

FROM ranked_events

WHERE event_rank = 1;
"""


def build_integrated_views() -> None:
    logger.info(
        "Creating integrated energy and operations views"
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(
                CREATE_EXECUTIVE_SNAPSHOT_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_ASSET_OPERATIONAL_KPI_VIEW_SQL
            )
        )

        connection.execute(
            text(
                CREATE_NEXT_CRITICAL_EVENT_VIEW_SQL
            )
        )

    logger.success(
        "Integrated analytical views created successfully"
    )


def main() -> None:
    build_integrated_views()


if __name__ == "__main__":
    main()