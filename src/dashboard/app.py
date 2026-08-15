from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from loguru import logger
from sqlalchemy import text

from src.config.database import get_engine


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Oil & Gas Operations Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# APPLICATION STYLE
# ============================================================

st.html(
    """
    <style>

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .stApp {
        background-color: #07111F;
        color: #F8FAFC;
    }

    header,
    header[data-testid="stHeader"],
    [data-testid="stHeader"],
    .stAppHeader,
    div[data-testid="stAppViewContainer"] > header {
        background-color: #07111F !important;
    }

    [data-testid="stSidebar"] {
        background-color: #0B1626;
        border-right: 1px solid #1E293B;
    }

    [data-testid="stSidebarContent"] {
        background-color: #0B1626;
    }

    h1,
    h2,
    h3,
    h4 {
        color: #F8FAFC;
    }

    .dashboard-title {
        font-size: 2.15rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.15rem;
    }

    .dashboard-subtitle {
        font-size: 1rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }

    .section-title {
        font-size: 1.25rem;
        font-weight: 650;
        color: #E2E8F0;
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
    }

    div[data-testid="stMetric"] {
        background-color: #0F1B2B;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 12px;
    }

    div[data-testid="stMetricLabel"] {
        color: #94A3B8;
    }

    div[data-testid="stMetricValue"] {
        color: #F8FAFC;
    }

    .status-success {
        border-left: 4px solid #22C55E;
        background: #0F1B2B;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .status-warning {
        border-left: 4px solid #F59E0B;
        background: #0F1B2B;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .status-danger {
        border-left: 4px solid #EF4444;
        background: #0F1B2B;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .small-muted {
        color: #94A3B8;
        font-size: 0.88rem;
    }

    hr {
        border-color: #1E293B;
    }

    </style>
    """
)


# ============================================================
# DATABASE
# ============================================================

@st.cache_resource
def get_database_engine():
    return get_engine()


def safe_query(
    query: str,
    params: dict | None = None,
) -> pd.DataFrame:
    """
    Execute SQL without crashing the dashboard.

    Returns an empty DataFrame when the query fails.
    """

    try:
        engine = get_database_engine()

        with engine.connect() as connection:
            return pd.read_sql(
                text(query),
                connection,
                params=params,
            )

    except Exception as error:

        logger.warning(
            "Dashboard query failed: {}",
            error,
        )

        st.warning(
            f"Data source currently unavailable: {error}"
        )

        return pd.DataFrame()


# ============================================================
# GENERIC HELPERS
# ============================================================

def first_existing_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    """
    Return the first candidate column found in a DataFrame.
    """

    for column in candidates:

        if column in dataframe.columns:
            return column

    return None


def safe_number(
    value,
    decimals: int = 1,
    default: str = "—",
) -> str:
    """
    Safely format numeric values.
    """

    if value is None:
        return default

    try:

        if pd.isna(value):
            return default

        return f"{float(value):,.{decimals}f}"

    except Exception:
        return str(value)


def safe_integer(
    value,
    default: str = "—",
) -> str:
    """
    Safely format integer-like values.
    """

    if value is None:
        return default

    try:

        if pd.isna(value):
            return default

        return f"{int(round(float(value))):,}"

    except Exception:
        return str(value)


def configure_plot(
    figure,
    height: int | None = None,
):
    """
    Apply common dashboard Plotly styling.
    """

    figure.update_layout(
        paper_bgcolor="#07111F",
        plot_bgcolor="#07111F",
        font=dict(
            color="#CBD5E1",
        ),
        margin=dict(
            l=10,
            r=10,
            t=45,
            b=10,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    if height is not None:

        figure.update_layout(
            height=height
        )

    return figure


# ============================================================
# DATA LOADERS
# ============================================================

@st.cache_data(ttl=120)
def load_assets() -> pd.DataFrame:

    return safe_query(
        """
        SELECT
            a.asset_key,
            a.asset_id,
            a.asset_name,
            a.asset_type,
            a.operator_name,
            a.is_active,

            a.max_wind_kmh,
            a.max_gust_kmh,
            a.max_wave_height_m,
            a.minimum_visibility_m,

            l.location_name,
            l.country,
            l.latitude,
            l.longitude

        FROM dim_asset AS a

        INNER JOIN dim_location AS l
            ON l.location_key = a.location_key

        WHERE
            a.is_active = TRUE

        ORDER BY
            a.asset_name;
        """
    )


@st.cache_data(ttl=120)
def load_asset_map() -> pd.DataFrame:
    """
    Retrieve active assets together with the earliest future
    operational risk in the latest forecast run.
    """

    return safe_query(
        """
        WITH latest_run AS
        (
            SELECT
                MAX(forecast_reference_time)
                    AS latest_reference_time
            FROM fact_operational_weather_risk
        ),

        current_asset_risk AS
        (
            SELECT DISTINCT ON (r.asset_key)

                r.asset_key,
                r.forecast_reference_time,
                r.forecast_valid_time,
                r.overall_risk_level

            FROM fact_operational_weather_risk AS r

            INNER JOIN latest_run AS lr
                ON r.forecast_reference_time =
                   lr.latest_reference_time

            WHERE
                r.forecast_valid_time >= CURRENT_TIMESTAMP

            ORDER BY
                r.asset_key,
                r.forecast_valid_time
        )

        SELECT

            a.asset_key,
            a.asset_id,
            a.asset_name,
            a.asset_type,
            a.operator_name,

            l.location_name,
            l.country,
            l.latitude,
            l.longitude,

            a.max_wind_kmh,
            a.max_gust_kmh,
            a.max_wave_height_m,
            a.minimum_visibility_m,

            r.forecast_reference_time,
            r.forecast_valid_time,

            COALESCE(
                r.overall_risk_level,
                'UNKNOWN'
            ) AS overall_risk_level

        FROM dim_asset AS a

        INNER JOIN dim_location AS l
            ON l.location_key = a.location_key

        LEFT JOIN current_asset_risk AS r
            ON r.asset_key = a.asset_key

        WHERE
            a.is_active = TRUE

        ORDER BY
            a.asset_name;
        """
    )


# ============================================================
# MAP
# ============================================================

def build_asset_map(
    dataframe: pd.DataFrame,
    selected_asset: str | None = None,
):
    """
    Build the interactive operational offshore asset map.
    """

    if dataframe.empty:
        return None

    required_columns = {
        "asset_name",
        "latitude",
        "longitude",
    }

    if not required_columns.issubset(
        dataframe.columns
    ):
        return None

    map_df = dataframe.dropna(
        subset=[
            "latitude",
            "longitude",
        ]
    ).copy()

    if map_df.empty:
        return None

    if "overall_risk_level" not in map_df.columns:

        map_df[
            "overall_risk_level"
        ] = "UNKNOWN"

    map_df[
        "overall_risk_level"
    ] = (
        map_df[
            "overall_risk_level"
        ]
        .fillna("UNKNOWN")
        .astype(str)
        .str.upper()
    )

    risk_colors = {
        "GREEN": "#22C55E",
        "AMBER": "#F59E0B",
        "RED": "#EF4444",
        "UNKNOWN": "#64748B",
    }

    # --------------------------------------------------------
    # MAIN ASSET LAYER
    # --------------------------------------------------------

    figure = px.scatter_map(
        map_df,
        lat="latitude",
        lon="longitude",
        color="overall_risk_level",
        color_discrete_map=risk_colors,
        hover_name="asset_name",
        hover_data={
            "asset_type": True,
            "operator_name": True,
            "location_name": True,
            "country": True,
            "forecast_valid_time": True,
            "max_wind_kmh": True,
            "max_gust_kmh": True,
            "max_wave_height_m": True,
            "minimum_visibility_m": True,
            "latitude": False,
            "longitude": False,
        },
        zoom=6,
        height=540,
        map_style="open-street-map",
    )

    figure.update_traces(
        marker=dict(
            size=17,
            opacity=0.95,
        ),
        selector=dict(
            type="scattermap"
        ),
    )

    # --------------------------------------------------------
    # SELECTED ASSET HIGHLIGHT
    # --------------------------------------------------------

    if selected_asset:

        selected_df = map_df[
            map_df["asset_name"]
            == selected_asset
        ]

        if not selected_df.empty:

            figure.add_trace(
                go.Scattermap(
                    lat=selected_df[
                        "latitude"
                    ],
                    lon=selected_df[
                        "longitude"
                    ],
                    mode="markers",
                    marker=dict(
                        size=31,
                        color="#38BDF8",
                        opacity=0.35,
                    ),
                    hoverinfo="skip",
                    name="Selected Asset",
                    showlegend=False,
                )
            )

    # --------------------------------------------------------
    # MAP POSITION
    # --------------------------------------------------------

    if (
        not map_df["latitude"].empty
        and not map_df["longitude"].empty
    ):

        center_lat = (
            map_df["latitude"]
            .astype(float)
            .mean()
        )

        center_lon = (
            map_df["longitude"]
            .astype(float)
            .mean()
        )

        figure.update_layout(
            map=dict(
                center=dict(
                    lat=center_lat,
                    lon=center_lon,
                ),
                zoom=6,
            )
        )

    figure.update_layout(
        margin=dict(
            l=0,
            r=0,
            t=10,
            b=0,
        ),
        legend_title_text="Operational Risk",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor="rgba(7,17,31,0.8)",
        ),
    )

    return figure


# ============================================================
# SIDEBAR
# ============================================================

assets_df = load_assets()

st.sidebar.markdown(
    """
    ## Oil & Gas Intelligence

    Offshore Energy  
    Data Engineering Platform
    """
)

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "Executive",
        "Offshore Operations",
        "Rig Market",
        "Energy Intelligence",
        "Data Quality",
    ],
)

selected_asset = None

if not assets_df.empty:

    asset_names = (
        assets_df[
            "asset_name"
        ]
        .dropna()
        .astype(str)
        .tolist()
    )

    if asset_names:

        selected_asset = st.sidebar.selectbox(
            "Monitored Asset",
            asset_names,
        )

st.sidebar.divider()

st.sidebar.caption(
    "Python • PostgreSQL • Docker • Streamlit"
)


# ============================================================
# EXECUTIVE PAGE
# ============================================================

def render_executive_page():

    st.markdown(
        '<div class="dashboard-title">'
        'Executive Operations'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Integrated offshore weather, drilling activity, '
        'energy pricing and pipeline health.'
        '</div>',
        unsafe_allow_html=True,
    )

    executive_df = safe_query(
        """
        SELECT *
        FROM vw_executive_energy_operations
        LIMIT 1;
        """
    )

    quality_df = safe_query(
        """
        SELECT *
        FROM vw_latest_quality_summary
        LIMIT 1;
        """
    )

    pipeline_df = safe_query(
        """
        SELECT *
        FROM vw_latest_pipeline_run
        LIMIT 1;
        """
    )

    # --------------------------------------------------------
    # EXECUTIVE KPIS
    # --------------------------------------------------------

    if not executive_df.empty:

        row = executive_df.iloc[0]

        col1, col2, col3, col4, col5 = (
            st.columns(5)
        )

        with col1:

            st.metric(
                "Latest Rig Count",
                safe_integer(
                    row.get(
                        "total_rig_count"
                    )
                ),
            )

        with col2:

            st.metric(
                "Countries Reporting",
                safe_integer(
                    row.get(
                        "countries_reporting"
                    )
                ),
            )

        with col3:

            st.metric(
                "Energy Price",
                safe_number(
                    row.get(
                        "average_energy_price_usd"
                    ),
                    3,
                ),
            )

        with col4:

            st.metric(
                "Monitored Assets",
                safe_integer(
                    row.get(
                        "monitored_assets"
                    )
                ),
            )

        with col5:

            st.metric(
                "RED Forecast Hours",
                safe_integer(
                    row.get(
                        "red_hours"
                    )
                ),
            )

        # ----------------------------------------------------
        # RISK DISTRIBUTION
        # ----------------------------------------------------

        st.divider()

        risk_data = pd.DataFrame(
            {
                "Risk": [
                    "GREEN",
                    "AMBER",
                    "RED",
                    "UNKNOWN",
                ],
                "Hours": [
                    row.get(
                        "green_hours",
                        0,
                    ),
                    row.get(
                        "amber_hours",
                        0,
                    ),
                    row.get(
                        "red_hours",
                        0,
                    ),
                    row.get(
                        "unknown_hours",
                        0,
                    ),
                ],
            }
        )

        risk_figure = px.bar(
            risk_data,
            x="Risk",
            y="Hours",
            color="Risk",
            color_discrete_map={
                "GREEN": "#22C55E",
                "AMBER": "#F59E0B",
                "RED": "#EF4444",
                "UNKNOWN": "#64748B",
            },
            title=(
                "Latest Offshore Forecast "
                "Risk Distribution"
            ),
        )

        configure_plot(
            risk_figure,
            380,
        )

        st.plotly_chart(
            risk_figure,
            use_container_width=True,
        )

    else:

        st.info(
            "Executive operational view is not available."
        )

    # --------------------------------------------------------
    # PIPELINE HEALTH
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Pipeline Health'
        '</div>',
        unsafe_allow_html=True,
    )

    health1, health2, health3 = (
        st.columns(3)
    )

    if not pipeline_df.empty:

        pipeline_row = (
            pipeline_df.iloc[0]
        )

        with health1:

            st.metric(
                "Pipeline Status",
                str(
                    pipeline_row.get(
                        "status",
                        "UNKNOWN",
                    )
                ),
            )

        with health2:

            duration = (
                pipeline_row.get(
                    "duration_seconds"
                )
            )

            duration_text = (
                safe_number(
                    duration,
                    1,
                )
            )

            if duration_text != "—":
                duration_text += " s"

            st.metric(
                "Duration",
                duration_text,
            )

    if not quality_df.empty:

        quality_row = (
            quality_df.iloc[0]
        )

        passed_col = (
            first_existing_column(
                quality_df,
                [
                    "passed_checks",
                    "checks_passed",
                    "passed",
                ],
            )
        )

        failed_col = (
            first_existing_column(
                quality_df,
                [
                    "failed_checks",
                    "checks_failed",
                    "failed",
                ],
            )
        )

        with health3:

            passed = (
                quality_row.get(
                    passed_col
                )
                if passed_col
                else None
            )

            failed = (
                quality_row.get(
                    failed_col
                )
                if failed_col
                else None
            )

            if passed is not None:

                st.metric(
                    "Quality Checks",
                    (
                        safe_integer(
                            passed
                        )
                        + " passed"
                    ),
                    delta=(
                        (
                            safe_integer(
                                failed
                            )
                            + " failed"
                        )
                        if failed is not None
                        else None
                    ),
                )


# ============================================================
# OFFSHORE OPERATIONS
# ============================================================

def render_offshore_page():

    st.markdown(
        '<div class="dashboard-title">'
        'Offshore Operations'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Geospatial asset monitoring, forecast conditions '
        'and operational weather risk.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ========================================================
    # MAP
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        'Monitored Offshore Assets'
        '</div>',
        unsafe_allow_html=True,
    )

    map_df = load_asset_map()

    asset_map = build_asset_map(
        map_df,
        selected_asset,
    )

    if asset_map is not None:

        st.plotly_chart(
            asset_map,
            use_container_width=True,
        )

        st.caption(
            "Marker color represents the earliest future "
            "operational risk from the latest forecast run. "
            "The larger cyan marker identifies the selected "
            "asset."
        )

    else:

        st.info(
            "No valid asset coordinates are available."
        )

    st.divider()

    # ========================================================
    # SELECTED ASSET
    # ========================================================

    if not selected_asset:

        st.info(
            "Select an offshore asset from the sidebar."
        )

        return

    st.markdown(
        (
            '<div class="section-title">'
            f'Selected Asset — {selected_asset}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    asset_info = assets_df[
        assets_df[
            "asset_name"
        ]
        == selected_asset
    ]

    if not asset_info.empty:

        asset_row = (
            asset_info.iloc[0]
        )

        a1, a2, a3, a4 = (
            st.columns(4)
        )

        with a1:

            st.metric(
                "Asset Type",
                str(
                    asset_row.get(
                        "asset_type",
                        "—",
                    )
                ),
            )

        with a2:

            value = safe_number(
                asset_row.get(
                    "max_wind_kmh"
                ),
                0,
            )

            st.metric(
                "Max Wind",
                (
                    value + " km/h"
                    if value != "—"
                    else "—"
                ),
            )

        with a3:

            value = safe_number(
                asset_row.get(
                    "max_wave_height_m"
                ),
                1,
            )

            st.metric(
                "Max Wave",
                (
                    value + " m"
                    if value != "—"
                    else "—"
                ),
            )

        with a4:

            value = safe_number(
                asset_row.get(
                    "minimum_visibility_m"
                ),
                0,
            )

            st.metric(
                "Min Visibility",
                (
                    value + " m"
                    if value != "—"
                    else "—"
                ),
            )

    # ========================================================
    # FORECAST
    # ========================================================

    forecast_df = safe_query(
        """
        SELECT *
        FROM vw_latest_offshore_forecast
        WHERE asset_name = :asset_name
        ORDER BY forecast_valid_time;
        """,
        {
            "asset_name": selected_asset,
        },
    )

    if forecast_df.empty:

        st.warning(
            "No forecast data available for this asset."
        )

        return

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    if (
        "forecast_valid_time"
        in forecast_df.columns
    ):

        forecast_df[
            "forecast_valid_time"
        ] = pd.to_datetime(
            forecast_df[
                "forecast_valid_time"
            ],
            errors="coerce",
        )

        forecast_df = (
            forecast_df
            .dropna(
                subset=[
                    "forecast_valid_time"
                ]
            )
            .sort_values(
                "forecast_valid_time"
            )
            .reset_index(
                drop=True
            )
        )

    # --------------------------------------------------------
    # CURRENT/FIRST FUTURE FORECAST
    # --------------------------------------------------------

    current_row = (
        forecast_df.iloc[0]
    )

    if (
        "forecast_valid_time"
        in forecast_df.columns
    ):

        future_df = forecast_df[
            forecast_df[
                "forecast_valid_time"
            ]
            >= pd.Timestamp.now()
        ]

        if not future_df.empty:

            current_row = (
                future_df.iloc[0]
            )

    # --------------------------------------------------------
    # KPIS
    # --------------------------------------------------------

    k1, k2, k3, k4, k5 = (
        st.columns(5)
    )

    with k1:

        st.metric(
            "Current Risk",
            str(
                current_row.get(
                    "overall_risk_level",
                    "UNKNOWN",
                )
            ),
        )

    with k2:

        value = safe_number(
            current_row.get(
                "wind_speed_kmh"
            ),
            1,
        )

        st.metric(
            "Wind",
            (
                value + " km/h"
                if value != "—"
                else "—"
            ),
        )

    with k3:

        value = safe_number(
            current_row.get(
                "wind_gust_kmh"
            ),
            1,
        )

        st.metric(
            "Gust",
            (
                value + " km/h"
                if value != "—"
                else "—"
            ),
        )

    with k4:

        value = safe_number(
            current_row.get(
                "wave_height_m"
            ),
            2,
        )

        st.metric(
            "Wave",
            (
                value + " m"
                if value != "—"
                else "—"
            ),
        )

    with k5:

        value = safe_number(
            current_row.get(
                "visibility_m"
            ),
            0,
        )

        st.metric(
            "Visibility",
            (
                value + " m"
                if value != "—"
                else "—"
            ),
        )

    st.divider()

    # ========================================================
    # WIND + GUST
    # ========================================================

    wind_columns = []

    if (
        "wind_speed_kmh"
        in forecast_df.columns
    ):
        wind_columns.append(
            "wind_speed_kmh"
        )

    if (
        "wind_gust_kmh"
        in forecast_df.columns
    ):
        wind_columns.append(
            "wind_gust_kmh"
        )

    if (
        wind_columns
        and "forecast_valid_time"
        in forecast_df.columns
    ):

        wind_long = (
            forecast_df.melt(
                id_vars=[
                    "forecast_valid_time"
                ],
                value_vars=wind_columns,
                var_name="Variable",
                value_name="km/h",
            )
        )

        wind_figure = px.line(
            wind_long,
            x="forecast_valid_time",
            y="km/h",
            color="Variable",
            title="Wind & Gust Forecast",
        )

        configure_plot(
            wind_figure,
            400,
        )

        wind_figure.update_layout(
            hovermode="x unified",
        )

        st.plotly_chart(
            wind_figure,
            use_container_width=True,
        )

    # ========================================================
    # WAVE + VISIBILITY
    # ========================================================

    chart1, chart2 = (
        st.columns(2)
    )

    with chart1:

        if (
            "wave_height_m"
            in forecast_df.columns
            and "forecast_valid_time"
            in forecast_df.columns
        ):

            wave_figure = px.line(
                forecast_df,
                x="forecast_valid_time",
                y="wave_height_m",
                title=(
                    "Significant Wave Height"
                ),
                labels={
                    "wave_height_m":
                        "Wave Height (m)",
                },
            )

            configure_plot(
                wave_figure,
                380,
            )

            st.plotly_chart(
                wave_figure,
                use_container_width=True,
            )

    with chart2:

        if (
            "visibility_m"
            in forecast_df.columns
            and "forecast_valid_time"
            in forecast_df.columns
        ):

            visibility_figure = px.line(
                forecast_df,
                x="forecast_valid_time",
                y="visibility_m",
                title="Visibility Forecast",
                labels={
                    "visibility_m":
                        "Visibility (m)",
                },
            )

            configure_plot(
                visibility_figure,
                380,
            )

            st.plotly_chart(
                visibility_figure,
                use_container_width=True,
            )

    # ========================================================
    # RISK TIMELINE
    # ========================================================

    if (
        "overall_risk_level"
        in forecast_df.columns
        and "forecast_valid_time"
        in forecast_df.columns
    ):

        st.markdown(
            '<div class="section-title">'
            'Operational Risk Timeline'
            '</div>',
            unsafe_allow_html=True,
        )

        risk_numeric = {
            "UNKNOWN": 0,
            "GREEN": 1,
            "AMBER": 2,
            "RED": 3,
        }

        risk_df = forecast_df[
            [
                "forecast_valid_time",
                "overall_risk_level",
            ]
        ].copy()

        risk_df[
            "overall_risk_level"
        ] = (
            risk_df[
                "overall_risk_level"
            ]
            .fillna("UNKNOWN")
            .astype(str)
            .str.upper()
        )

        risk_df[
            "risk_score"
        ] = (
            risk_df[
                "overall_risk_level"
            ]
            .map(
                risk_numeric
            )
            .fillna(0)
        )

        risk_figure = px.scatter(
            risk_df,
            x="forecast_valid_time",
            y="risk_score",
            color="overall_risk_level",
            color_discrete_map={
                "GREEN": "#22C55E",
                "AMBER": "#F59E0B",
                "RED": "#EF4444",
                "UNKNOWN": "#64748B",
            },
            labels={
                "risk_score":
                    "Operational Risk",
                "forecast_valid_time":
                    "Forecast Time",
            },
        )

        risk_figure.update_traces(
            marker=dict(
                size=11
            )
        )

        risk_figure.update_yaxes(
            tickmode="array",
            tickvals=[
                0,
                1,
                2,
                3,
            ],
            ticktext=[
                "UNKNOWN",
                "GREEN",
                "AMBER",
                "RED",
            ],
        )

        configure_plot(
            risk_figure,
            360,
        )

        st.plotly_chart(
            risk_figure,
            use_container_width=True,
        )

    # ========================================================
    # NEXT CRITICAL EVENT
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        'Next Critical Weather Event'
        '</div>',
        unsafe_allow_html=True,
    )

    critical_df = safe_query(
        """
        SELECT *
        FROM vw_next_weather_critical_event
        WHERE asset_name = :asset_name
        LIMIT 1;
        """,
        {
            "asset_name": selected_asset,
        },
    )

    if not critical_df.empty:

        critical_row = (
            critical_df.iloc[0]
        )

        risk_level = str(
            critical_row.get(
                "overall_risk_level",
                "UNKNOWN",
            )
        ).upper()

        valid_time = (
            critical_row.get(
                "forecast_valid_time",
                critical_row.get(
                    "critical_time",
                    "—",
                ),
            )
        )

        if risk_level == "RED":

            st.markdown(
                f"""
                <div class="status-danger">
                    <b>RED operational risk expected</b><br>
                    Forecast time: {valid_time}
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                f"""
                <div class="status-warning">
                    <b>{risk_level} operational risk expected</b><br>
                    Forecast time: {valid_time}
                </div>
                """,
                unsafe_allow_html=True,
            )

    else:

        st.markdown(
            """
            <div class="status-success">
                <b>No upcoming AMBER or RED event detected
                in the available forecast window.</b>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# RIG MARKET
# ============================================================

def render_rig_page():

    st.markdown(
        '<div class="dashboard-title">'
        'Rig Market Intelligence'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Historical drilling activity from the '
        'Baker Hughes Worldwide Rig Count.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ========================================================
    # LOAD DATA
    # ========================================================

    latest_df = safe_query(
        """
        SELECT *
        FROM vw_latest_rig_count;
        """
    )

    region_df = safe_query(
        """
        SELECT *
        FROM vw_rig_count_region_monthly;
        """
    )

    # ========================================================
    # KPI CARDS
    # ========================================================

    if not latest_df.empty:

        latest_count_col = (
            first_existing_column(
                latest_df,
                [
                    "rig_count",
                    "total_rig_count",
                ],
            )
        )

        country_col = (
            first_existing_column(
                latest_df,
                [
                    "country",
                    "country_name",
                ],
            )
        )

        r1, r2 = (
            st.columns(2)
        )

        with r1:

            if latest_count_col:

                st.metric(
                    "Latest Rig Count",
                    safe_integer(
                        latest_df[
                            latest_count_col
                        ].sum()
                    ),
                )

            else:

                st.metric(
                    "Latest Rig Count",
                    "—",
                )

        with r2:

            if country_col:

                st.metric(
                    "Countries Reporting",
                    latest_df[
                        country_col
                    ].nunique(),
                )

            else:

                st.metric(
                    "Countries Reporting",
                    "—",
                )

    if region_df.empty:

        st.warning(
            "Rig market data is unavailable."
        )

        return

    # ========================================================
    # DETECT COLUMNS
    # ========================================================

    date_col = (
        first_existing_column(
            region_df,
            [
                "observation_date",
                "date",
            ],
        )
    )

    region_col = (
        first_existing_column(
            region_df,
            [
                "region",
                "region_name",
            ],
        )
    )

    rig_col = (
        first_existing_column(
            region_df,
            [
                "rig_count",
                "total_rig_count",
            ],
        )
    )

    # ========================================================
    # NORMALIZE
    # ========================================================

    if date_col:

        region_df[
            date_col
        ] = pd.to_datetime(
            region_df[
                date_col
            ],
            errors="coerce",
        )

        region_df = (
            region_df
            .dropna(
                subset=[
                    date_col
                ]
            )
            .sort_values(
                date_col
            )
            .reset_index(
                drop=True
            )
        )

    missing_columns = []

    if date_col is None:
        missing_columns.append(
            "date"
        )

    if region_col is None:
        missing_columns.append(
            "region"
        )

    if rig_col is None:
        missing_columns.append(
            "rig count"
        )

    if missing_columns:

        st.warning(
            "Rig market view does not contain "
            "the required analytical columns: "
            + ", ".join(
                missing_columns
            )
        )

        with st.expander(
            "Inspect Rig View Columns"
        ):

            st.write(
                region_df.columns.tolist()
            )

            st.dataframe(
                region_df.head(20),
                use_container_width=True,
                hide_index=True,
            )

        return

    # ========================================================
    # REGIONAL HISTORY
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        'Regional Drilling Activity'
        '</div>',
        unsafe_allow_html=True,
    )

    rig_figure = px.line(
        region_df,
        x=date_col,
        y=rig_col,
        color=region_col,
        title="Worldwide Rig Count by Region",
        labels={
            date_col:
                "Date",
            rig_col:
                "Rig Count",
            region_col:
                "Region",
        },
    )

    configure_plot(
        rig_figure,
        520,
    )

    rig_figure.update_layout(
        hovermode="x unified",
    )

    rig_figure.update_xaxes(
        showgrid=False,
    )

    rig_figure.update_yaxes(
        rangemode="tozero",
    )

    st.plotly_chart(
        rig_figure,
        use_container_width=True,
    )

    # ========================================================
    # LATEST REGIONAL SNAPSHOT
    # ========================================================

    latest_date = (
        region_df[
            date_col
        ].max()
    )

    latest_region_df = (
        region_df[
            region_df[
                date_col
            ]
            == latest_date
        ]
        .copy()
    )

    if not latest_region_df.empty:

        latest_region_df = (
            latest_region_df
            .sort_values(
                rig_col,
                ascending=False,
            )
        )

        st.markdown(
            '<div class="section-title">'
            'Latest Regional Snapshot'
            '</div>',
            unsafe_allow_html=True,
        )

        regional_bar = px.bar(
            latest_region_df,
            x=region_col,
            y=rig_col,
            title=(
                "Rig Count by Region — "
                f"{latest_date:%Y-%m}"
            ),
            labels={
                region_col:
                    "Region",
                rig_col:
                    "Rig Count",
            },
        )

        configure_plot(
            regional_bar,
            420,
        )

        regional_bar.update_xaxes(
            categoryorder=(
                "total descending"
            )
        )

        regional_bar.update_yaxes(
            rangemode="tozero",
        )

        st.plotly_chart(
            regional_bar,
            use_container_width=True,
        )

    # ========================================================
    # TABLE
    # ========================================================

    with st.expander(
        "View Rig Market Data"
    ):

        display_df = (
            region_df.copy()
        )

        display_df[
            date_col
        ] = (
            display_df[
                date_col
            ]
            .dt.strftime(
                "%Y-%m-%d"
            )
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# ENERGY INTELLIGENCE
# ============================================================

def render_energy_page():

    st.markdown(
        '<div class="dashboard-title">'
        'Energy Intelligence'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'EIA energy-price analytics integrated into '
        'the operational warehouse.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "The current EIA dataset represents a refined "
        "petroleum product price series. It is presented "
        "as Energy Price rather than WTI crude."
    )

    # ========================================================
    # LOAD
    # ========================================================

    energy_df = safe_query(
        """
        SELECT *
        FROM vw_daily_oil_price;
        """
    )

    if energy_df.empty:

        st.warning(
            "Energy-price data is unavailable."
        )

        return

    # ========================================================
    # DETECT COLUMNS
    # ========================================================

    date_col = (
        first_existing_column(
            energy_df,
            [
                "price_date",
                "date",
                "timestamp",
            ],
        )
    )

    price_col = (
        first_existing_column(
            energy_df,
            [
                "average_price_usd",
                "price_usd",
                "price",
            ],
        )
    )

    product_col = (
        first_existing_column(
            energy_df,
            [
                "product_name",
                "product",
                "product_code",
            ],
        )
    )

    unit_col = (
        first_existing_column(
            energy_df,
            [
                "unit",
                "default_unit",
            ],
        )
    )

    # ========================================================
    # NORMALIZE DATE
    # ========================================================

    if date_col:

        energy_df[
            date_col
        ] = pd.to_datetime(
            energy_df[
                date_col
            ],
            errors="coerce",
        )

        energy_df = (
            energy_df
            .dropna(
                subset=[
                    date_col
                ]
            )
            .sort_values(
                date_col
            )
            .reset_index(
                drop=True
            )
        )

    # ========================================================
    # VALIDATE
    # ========================================================

    if date_col is None or price_col is None:

        st.warning(
            "Energy-price view does not contain "
            "the expected analytical columns."
        )

        with st.expander(
            "Inspect Energy View Columns"
        ):

            st.write(
                energy_df.columns.tolist()
            )

            st.dataframe(
                energy_df.head(20),
                use_container_width=True,
                hide_index=True,
            )

        return

    # ========================================================
    # KPIS
    # ========================================================

    e1, e2, e3, e4 = (
        st.columns(4)
    )

    latest_row = (
        energy_df.iloc[-1]
    )

    with e1:

        latest_value = safe_number(
            latest_row.get(
                price_col
            ),
            3,
        )

        if (
            unit_col
            and unit_col
            in energy_df.columns
        ):

            unit = str(
                latest_row.get(
                    unit_col,
                    "",
                )
            )

            if (
                unit
                and unit.lower()
                != "nan"
            ):
                latest_value += (
                    f" {unit}"
                )

        st.metric(
            "Latest Price",
            latest_value,
        )

    with e2:

        st.metric(
            "Average Price",
            safe_number(
                energy_df[
                    price_col
                ].mean(),
                3,
            ),
        )

    with e3:

        st.metric(
            "Minimum",
            safe_number(
                energy_df[
                    price_col
                ].min(),
                3,
            ),
        )

    with e4:

        st.metric(
            "Maximum",
            safe_number(
                energy_df[
                    price_col
                ].max(),
                3,
            ),
        )

    # ========================================================
    # PRICE HISTORY
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        'Energy Price History'
        '</div>',
        unsafe_allow_html=True,
    )

    line_kwargs = {}

    if product_col:

        line_kwargs[
            "color"
        ] = product_col

    energy_figure = px.line(
        energy_df,
        x=date_col,
        y=price_col,
        title="EIA Energy Price History",
        labels={
            date_col:
                "Date",
            price_col:
                "Price",
        },
        **line_kwargs,
    )

    configure_plot(
        energy_figure,
        500,
    )

    energy_figure.update_layout(
        hovermode="x unified",
    )

    st.plotly_chart(
        energy_figure,
        use_container_width=True,
    )

    # ========================================================
    # DATASET
    # ========================================================

    with st.expander(
        "View Energy Dataset"
    ):

        display_energy = (
            energy_df.copy()
        )

        display_energy[
            date_col
        ] = (
            display_energy[
                date_col
            ]
            .dt.strftime(
                "%Y-%m-%d"
            )
        )

        st.dataframe(
            display_energy,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# DATA QUALITY
# ============================================================

def render_quality_page():

    st.markdown(
        '<div class="dashboard-title">'
        'Data Quality & Observability'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Pipeline execution health, persisted quality checks '
        'and warehouse monitoring.'
        '</div>',
        unsafe_allow_html=True,
    )

    pipeline_df = safe_query(
        """
        SELECT *
        FROM vw_latest_pipeline_run
        LIMIT 1;
        """
    )

    quality_summary_df = safe_query(
        """
        SELECT *
        FROM vw_latest_quality_summary
        LIMIT 1;
        """
    )

    quality_checks_df = safe_query(
        """
        SELECT *
        FROM vw_latest_quality_checks;
        """
    )

    history_df = safe_query(
        """
        SELECT *
        FROM vw_pipeline_run_history;
        """
    )

    # ========================================================
    # KPI ROW
    # ========================================================

    q1, q2, q3, q4 = (
        st.columns(4)
    )

    if not pipeline_df.empty:

        row = (
            pipeline_df.iloc[0]
        )

        with q1:

            st.metric(
                "Latest Pipeline",
                str(
                    row.get(
                        "status",
                        "UNKNOWN",
                    )
                ),
            )

        with q4:

            duration_value = safe_number(
                row.get(
                    "duration_seconds"
                ),
                1,
            )

            st.metric(
                "Duration",
                (
                    duration_value + " s"
                    if duration_value
                    != "—"
                    else "—"
                ),
            )

    if not quality_summary_df.empty:

        row = (
            quality_summary_df.iloc[0]
        )

        passed_col = (
            first_existing_column(
                quality_summary_df,
                [
                    "passed_checks",
                    "checks_passed",
                    "passed",
                ],
            )
        )

        failed_col = (
            first_existing_column(
                quality_summary_df,
                [
                    "failed_checks",
                    "checks_failed",
                    "failed",
                ],
            )
        )

        with q2:

            if passed_col:

                st.metric(
                    "Checks Passed",
                    safe_integer(
                        row.get(
                            passed_col
                        )
                    ),
                )

        with q3:

            if failed_col:

                st.metric(
                    "Checks Failed",
                    safe_integer(
                        row.get(
                            failed_col
                        )
                    ),
                )

    st.divider()

    # ========================================================
    # CHECK TABLE
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        'Latest Warehouse Quality Checks'
        '</div>',
        unsafe_allow_html=True,
    )

    if not quality_checks_df.empty:

        st.dataframe(
            quality_checks_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No persisted quality-check results available."
        )

    # ========================================================
    # PIPELINE HISTORY
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        'Pipeline Run History'
        '</div>',
        unsafe_allow_html=True,
    )

    if history_df.empty:

        st.info(
            "No pipeline history available."
        )

        return

    started_col = (
        first_existing_column(
            history_df,
            [
                "started_at",
                "start_time",
            ],
        )
    )

    duration_col = (
        first_existing_column(
            history_df,
            [
                "duration_seconds",
                "duration",
            ],
        )
    )

    status_col = (
        first_existing_column(
            history_df,
            [
                "status",
            ],
        )
    )

    if started_col:

        history_df[
            started_col
        ] = pd.to_datetime(
            history_df[
                started_col
            ],
            errors="coerce",
        )

        history_df = (
            history_df
            .sort_values(
                started_col
            )
            .reset_index(
                drop=True
            )
        )

    if (
        started_col
        and duration_col
    ):

        history_figure = px.bar(
            history_df,
            x=started_col,
            y=duration_col,
            color=(
                status_col
                if status_col
                else None
            ),
            title=(
                "Pipeline Execution Duration"
            ),
            color_discrete_map={
                "SUCCESS": "#22C55E",
                "FAILED": "#EF4444",
                "RUNNING": "#38BDF8",
            },
        )

        configure_plot(
            history_figure,
            400,
        )

        st.plotly_chart(
            history_figure,
            use_container_width=True,
        )

    with st.expander(
        "View Pipeline Run History"
    ):

        st.dataframe(
            history_df.sort_values(
                started_col,
                ascending=False,
            )
            if started_col
            else history_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# PAGE ROUTER
# ============================================================

if page == "Executive":

    render_executive_page()

elif page == "Offshore Operations":

    render_offshore_page()

elif page == "Rig Market":

    render_rig_page()

elif page == "Energy Intelligence":

    render_energy_page()

elif page == "Data Quality":

    render_quality_page()