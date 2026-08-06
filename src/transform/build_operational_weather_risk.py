from pathlib import Path

import pandas as pd
from loguru import logger

from src.config.config import (
    ASSET_REGISTRY_FILE,
    ATMOSPHERIC_PARQUET_FILE,
    MARINE_PARQUET_FILE,
    PROCESSED_WEATHER_FOLDER,
)


OUTPUT_FILE = (
    PROCESSED_WEATHER_FOLDER
    / "operational_weather_risk.parquet"
)


RISK_PRIORITY = {
    "UNKNOWN": 0,
    "GREEN": 1,
    "AMBER": 2,
    "RED": 3,
}


def classify_upper_limit(
    value: float | None,
    limit: float,
) -> str:
    """
    GREEN: value below 80% of limit.
    AMBER: value between 80% and 100% of limit.
    RED: value above the operational limit.
    """

    if pd.isna(value):
        return "UNKNOWN"

    if value > limit:
        return "RED"

    if value >= limit * 0.80:
        return "AMBER"

    return "GREEN"


def classify_minimum_limit(
    value: float | None,
    minimum: float,
) -> str:
    """
    Used for visibility, where lower values represent
    greater operational risk.
    """

    if pd.isna(value):
        return "UNKNOWN"

    if value < minimum:
        return "RED"

    if value <= minimum * 1.25:
        return "AMBER"

    return "GREEN"


def highest_risk(
    risk_levels: list[str],
) -> str:
    return max(
        risk_levels,
        key=lambda level: RISK_PRIORITY[level],
    )


def build_recommendation(
    overall_risk: str,
    limiting_parameter: str | None,
) -> str:
    if overall_risk == "RED":
        return (
            "Suspend weather-sensitive operations; "
            f"limiting parameter: {limiting_parameter}."
        )

    if overall_risk == "AMBER":
        return (
            "Proceed with caution and enhanced monitoring; "
            f"limiting parameter: {limiting_parameter}."
        )

    if overall_risk == "GREEN":
        return (
            "Conditions are within configured operational "
            "limits."
        )

    return (
        "Insufficient data for a complete operational "
        "assessment."
    )


def build_operational_risk() -> Path:
    logger.info(
        "Building operational offshore weather risk"
    )

    assets = pd.read_csv(
        ASSET_REGISTRY_FILE
    )

    atmospheric = pd.read_parquet(
        ATMOSPHERIC_PARQUET_FILE
    )

    marine = pd.read_parquet(
        MARINE_PARQUET_FILE
    )

    merged = atmospheric.merge(
        marine[
            [
                "asset_id",
                "forecast_reference_time",
                "forecast_valid_time",
                "wave_height_m",
            ]
        ],
        on=[
            "asset_id",
            "forecast_reference_time",
            "forecast_valid_time",
        ],
        how="left",
        validate="one_to_one",
    )

    merged = merged.merge(
        assets[
            [
                "asset_id",
                "max_wind_kmh",
                "max_gust_kmh",
                "max_wave_height_m",
                "minimum_visibility_m",
            ]
        ],
        on="asset_id",
        how="left",
        validate="many_to_one",
    )

    risk_records = []

    for row in merged.itertuples(index=False):
        wind_risk = classify_upper_limit(
            row.wind_speed_kmh,
            row.max_wind_kmh,
        )

        gust_risk = classify_upper_limit(
            row.wind_gust_kmh,
            row.max_gust_kmh,
        )

        wave_risk = classify_upper_limit(
            row.wave_height_m,
            row.max_wave_height_m,
        )

        visibility_risk = classify_minimum_limit(
            row.visibility_m,
            row.minimum_visibility_m,
        )

        risks = {
            "wind_speed": wind_risk,
            "wind_gust": gust_risk,
            "wave_height": wave_risk,
            "visibility": visibility_risk,
        }

        overall_risk = highest_risk(
            list(risks.values())
        )

        limiting_parameter = max(
            risks,
            key=lambda parameter:
                RISK_PRIORITY[risks[parameter]],
        )

        if overall_risk == "GREEN":
            limiting_parameter = None

        risk_records.append(
            {
                "forecast_reference_time":
                    row.forecast_reference_time,

                "forecast_valid_time":
                    row.forecast_valid_time,

                "asset_id":
                    row.asset_id,

                "wind_risk_level":
                    wind_risk,

                "gust_risk_level":
                    gust_risk,

                "wave_risk_level":
                    wave_risk,

                "visibility_risk_level":
                    visibility_risk,

                "overall_risk_level":
                    overall_risk,

                "operation_recommendation":
                    build_recommendation(
                        overall_risk,
                        limiting_parameter,
                    ),

                "limiting_parameter":
                    limiting_parameter,

                "source":
                    "Operational Risk Engine v1",
            }
        )

    risk_dataframe = pd.DataFrame(
        risk_records
    )

    risk_dataframe = risk_dataframe.drop_duplicates(
        subset=[
            "asset_id",
            "forecast_reference_time",
            "forecast_valid_time",
        ],
        keep="last",
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    risk_dataframe.to_parquet(
        OUTPUT_FILE,
        index=False,
    )

    logger.success(
        "Operational risk Parquet saved: {} rows to {}",
        len(risk_dataframe),
        OUTPUT_FILE,
    )

    print("\nRisk distribution:")
    print(
        risk_dataframe[
            "overall_risk_level"
        ].value_counts(
            dropna=False
        )
    )

    print("\nRisk preview:")
    print(
        risk_dataframe.head(10).to_string(
            index=False
        )
    )

    return OUTPUT_FILE


def main() -> None:
    build_operational_risk()


if __name__ == "__main__":
    main()