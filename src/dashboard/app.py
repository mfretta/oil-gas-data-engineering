from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

from src.config.database import get_engine


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Oil & Gas Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="locked",
)


# ============================================================
# THEME / CSS
# ============================================================

st.html(
    """
    <style>

    /* ======================================================
       ROOT COLORS
       ====================================================== */

    :root {
        --app-bg: #07111f;
        --app-bg-2: #0b1626;
        --sidebar-bg: #07101d;
        --panel-bg: #101d2d;
        --panel-bg-2: #0d1928;

        --text-main: #f8fafc;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;

        --blue: #38bdf8;
        --green: #22c55e;
        --amber: #f59e0b;
        --red: #ef4444;
    }


    /* ======================================================
       GLOBAL APP
       ====================================================== */

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .stApp {
        background:
            linear-gradient(
                180deg,
                var(--app-bg) 0%,
                var(--app-bg-2) 100%
            ) !important;

        color: var(--text-main) !important;
    }

    html,
    body {
        font-family:
            Inter,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
    }


    /* ======================================================
       FIX STREAMLIT WHITE HEADER
       IMPORTANT:
       We COLOR the header.
       We DO NOT hide or collapse it.
       ====================================================== */

    header,
    header[data-testid="stHeader"],
    [data-testid="stHeader"],
    .stAppHeader,
    div[data-testid="stAppViewContainer"] > header {
        background: #07111f !important;
        background-color: #07111f !important;
        color: #cbd5e1 !important;
        box-shadow: none !important;
        border-bottom: 1px solid rgba(148, 163, 184, 0.08) !important;
    }

    header * {
        color: #94a3b8 !important;
    }

    [data-testid="stToolbar"],
    [data-testid="stToolbarActions"],
    [data-testid="stMainMenu"],
    [data-testid="stStatusWidget"] {
        background: transparent !important;
    }

    [data-testid="stDecoration"] {
        background: transparent !important;
    }


    /* ======================================================
       MAIN CONTENT
       ====================================================== */

    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 3rem !important;
        max-width: 1650px !important;
    }


    /* ======================================================
       SIDEBAR
       ====================================================== */

    [data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #07101d 0%,
                #091523 100%
            ) !important;

        border-right:
            1px solid rgba(148, 163, 184, 0.10) !important;
    }

    [data-testid="stSidebarContent"] {
        background: transparent !important;
    }

    [data-testid="stSidebar"] * {
        color: #cbd5e1;
    }

    [data-testid="stSidebar"] label {
        color: #cbd5e1 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(148, 163, 184, 0.10);
    }


    /* ======================================================
       RADIO NAVIGATION
       ====================================================== */

    [data-testid="stRadio"] label {
        color: #cbd5e1 !important;
    }

    [data-testid="stRadio"] p {
        color: #cbd5e1 !important;
    }


    /* ======================================================
       HERO
       ====================================================== */

    .hero {
        padding: 30px 32px;
        margin-bottom: 28px;

        border-radius: 20px;

        background:
            radial-gradient(
                circle at top right,
                rgba(14, 165, 233, 0.25),
                transparent 36%
            ),
            linear-gradient(
                135deg,
                #101c30,
                #10344a
            );

        border:
            1px solid rgba(148, 163, 184, 0.20);

        box-shadow:
            0 18px 45px rgba(0, 0, 0, 0.22);
    }

    .hero-eyebrow {
        color: #38bdf8;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.7px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    .hero-title {
        color: #f8fafc;
        font-size: 36px;
        line-height: 1.15;
        font-weight: 760;
        margin-bottom: 10px;
    }

    .hero-description {
        color: #a6b8cc;
        font-size: 15px;
        line-height: 1.6;
        max-width: 1050px;
    }


    /* ======================================================
       SECTION HEADERS
       ====================================================== */

    .section-label {
        margin-top: 18px;
        margin-bottom: 6px;

        color: #6e93bd;

        text-transform: uppercase;
        letter-spacing: 1.4px;

        font-size: 11px;
        font-weight: 700;
    }

    .section-title {
        color: #f8fafc;
        font-size: 23px;
        font-weight: 700;
        margin-bottom: 18px;
    }


    /* ======================================================
       FRESHNESS
       ====================================================== */

    .freshness-bar {
        padding: 13px 18px;
        margin-bottom: 26px;

        border-radius: 12px;

        background: rgba(15, 27, 43, 0.94);

        border:
            1px solid rgba(148, 163, 184, 0.14);

        color: #9db1c8;

        font-size: 12px;
    }

    .freshness-bar b {
        color: #dbeafe;
    }


    /* ======================================================
       KPI CARDS
       ====================================================== */

    .kpi-card {
        min-height: 125px;
        padding: 20px;

        border-radius: 17px;

        background:
            linear-gradient(
                145deg,
                #122033,
                #0f1b2b
            );

        border:
            1px solid rgba(148, 163, 184, 0.14);

        box-shadow:
            0 8px 30px rgba(0, 0, 0, 0.15);
    }

    .kpi-label {
        color: #8fb3dc;

        font-size: 12px;
        font-weight: 650;

        text-transform: uppercase;
        letter-spacing: 0.7px;

        margin-bottom: 12px;
    }

    .kpi-value {
        color: #f8fafc;

        font-size: 30px;
        line-height: 1;

        font-weight: 760;

        margin-bottom: 12px;
    }

    .kpi-note {
        color: #7089a6;
        font-size: 12px;
        line-height: 1.4;
    }

    .status-green {
        border-left: 4px solid #22c55e;
    }

    .status-amber {
        border-left: 4px solid #f59e0b;
    }

    .status-red {
        border-left: 4px solid #ef4444;
    }

    .green-text {
        color: #2ee67c;
    }

    .amber-text {
        color: #ffb71b;
    }

    .red-text {
        color: #ff5e66;
    }


    /* ======================================================
       SELECTBOX
       ====================================================== */

    [data-baseweb="select"] > div {
        background: #f8fafc !important;
        border-radius: 10px !important;
    }

    [data-baseweb="select"] span {
        color: #0f172a !important;
    }


    /* ======================================================
       TABS
       ====================================================== */

    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #f8fafc !important;
    }


    /* ======================================================
       DATAFRAME
       ====================================================== */

    [data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;

        border:
            1px solid rgba(148, 163, 184, 0.13);
    }


    /* ======================================================
       BUTTONS
       ====================================================== */

    .stDownloadButton button {
        background:
            rgba(14, 165, 233, 0.10) !important;

        color: #e0f2fe !important;

        border:
            1px solid rgba(56, 189, 248, 0.35) !important;

        border-radius: 10px !important;
    }

    .stDownloadButton button:hover {
        background:
            rgba(14, 165, 233, 0.18) !important;

        border-color:
            #38bdf8 !important;
    }

    </style>
    """
)


# ============================================================
# DATABASE
# ============================================================

engine = get_engine()


@st.cache_data(ttl=300)
def load_query(query: str) -> pd.DataFrame:
    with engine.connect() as connection:
        return pd.read_sql(
            text(query),
            connection,
        )


def safe_query(
    query: str,
    dataset_name: str,
) -> pd.DataFrame:
    try:
        return load_query(query)

    except Exception as error:
        st.warning(
            f"{dataset_name} could not be loaded."
        )

        st.caption(
            str(error)
        )

        return pd.DataFrame()


# ============================================================
# DATA
# ============================================================

executive = safe_query(
    """
    SELECT *
    FROM vw_executive_energy_operations;
    """,
    "Executive data",
)


assets = safe_query(
    """
    SELECT *
    FROM vw_asset_operational_kpis
    ORDER BY asset_name;
    """,
    "Asset KPI data",
)


weather = safe_query(
    """
    SELECT *
    FROM vw_latest_offshore_forecast
    ORDER BY
        asset_name,
        forecast_valid_time;
    """,
    "Weather forecast data",
)


critical = safe_query(
    """
    SELECT *
    FROM vw_next_weather_critical_event
    ORDER BY forecast_valid_time;
    """,
    "Critical weather data",
)


rig = safe_query(
    """
    SELECT *
    FROM vw_rig_count_region_monthly
    ORDER BY date;
    """,
    "Rig-count data",
)


energy = safe_query(
    """
    SELECT *
    FROM vw_daily_oil_price
    ORDER BY date;
    """,
    "Energy price data",
)


pipeline_run = safe_query(
    """
    SELECT *
    FROM vw_latest_pipeline_run;
    """,
    "Latest pipeline run",
)


quality_summary = safe_query(
    """
    SELECT *
    FROM vw_latest_quality_summary;
    """,
    "Latest quality summary",
)


quality_checks = safe_query(
    """
    SELECT *
    FROM vw_latest_quality_checks
    ORDER BY
        passed ASC,
        check_name;
    """,
    "Quality checks",
)


pipeline_history = safe_query(
    """
    SELECT *
    FROM vw_pipeline_run_history
    ORDER BY started_at DESC
    LIMIT 20;
    """,
    "Pipeline history",
)


warehouse_volume = safe_query(
    """
    SELECT
        'Atmospheric Forecast' AS dataset,
        COUNT(*) AS row_count,
        MAX(forecast_reference_time) AS latest_update
    FROM fact_weather_forecast

    UNION ALL

    SELECT
        'Marine Forecast',
        COUNT(*),
        MAX(forecast_reference_time)
    FROM fact_marine_forecast

    UNION ALL

    SELECT
        'Operational Risk',
        COUNT(*),
        MAX(forecast_reference_time)
    FROM fact_operational_weather_risk

    UNION ALL

    SELECT
        'Rig Count',
        COUNT(*),
        MAX(t.timestamp)
    FROM fact_rig_count AS f
    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key

    UNION ALL

    SELECT
        'Energy Price',
        COUNT(*),
        MAX(t.timestamp)
    FROM fact_oil_price AS f
    INNER JOIN dim_time AS t
        ON t.time_key = f.time_key;
    """,
    "Warehouse volume",
)


# ============================================================
# HELPERS
# ============================================================

def style_chart(
    figure,
    height: int = 400,
):
    figure.update_layout(
        height=height,

        margin=dict(
            l=20,
            r=20,
            t=55,
            b=20,
        ),

        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        font=dict(
            color="#b8c8da",
        ),

        title_font=dict(
            size=16,
            color="#f8fafc",
        ),

        legend=dict(
            bgcolor="rgba(0,0,0,0)",
        ),

        xaxis=dict(
            gridcolor=
                "rgba(148,163,184,0.08)",
        ),

        yaxis=dict(
            gridcolor=
                "rgba(148,163,184,0.08)",
        ),
    )

    return figure


def hero(
    eyebrow: str,
    title: str,
    description: str,
):
    st.html(
        f"""
        <div class="hero">

            <div class="hero-eyebrow">
                {eyebrow}
            </div>

            <div class="hero-title">
                {title}
            </div>

            <div class="hero-description">
                {description}
            </div>

        </div>
        """
    )


def section_header(
    eyebrow: str,
    title: str,
):
    st.html(
        f"""
        <div class="section-label">
            {eyebrow}
        </div>

        <div class="section-title">
            {title}
        </div>
        """
    )


def kpi_card(
    label: str,
    value: str,
    note: str,
    status: str | None = None,
):
    card_class = "kpi-card"
    value_class = "kpi-value"

    if status == "GREEN":
        card_class += " status-green"
        value_class += " green-text"

    elif status == "AMBER":
        card_class += " status-amber"
        value_class += " amber-text"

    elif status == "RED":
        card_class += " status-red"
        value_class += " red-text"

    st.html(
        f"""
        <div class="{card_class}">

            <div class="kpi-label">
                {label}
            </div>

            <div class="{value_class}">
                {value}
            </div>

            <div class="kpi-note">
                {note}
            </div>

        </div>
        """
    )


def csv_bytes(
    dataframe: pd.DataFrame,
) -> bytes:
    return dataframe.to_csv(
        index=False
    ).encode("utf-8")


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.html(
        """
        <div style="
            font-size:26px;
            font-weight:760;
            color:#f8fafc;
            margin-bottom:4px;
        ">
            ◈ O&G Intelligence
        </div>

        <div style="
            color:#6fa8df;
            font-size:12px;
            margin-bottom:28px;
        ">
            Operations Data Platform
        </div>
        """
    )

    st.caption(
        "NAVIGATION"
    )

    page = st.radio(
        "Navigation",
        [
            "Executive",
            "Offshore Operations",
            "Rig Market",
            "Energy Intelligence",
            "Data Quality",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown(
        "#### Global Filters"
    )

    asset_names = []

    if not assets.empty:
        asset_names = (
            assets["asset_name"]
            .dropna()
            .sort_values()
            .unique()
            .tolist()
        )

    selected_asset = st.selectbox(
        "Asset",
        ["All Assets"] + asset_names,
    )

    st.divider()

    if not pipeline_run.empty:

        sidebar_run = (
            pipeline_run.iloc[0]
        )

        status = str(
            sidebar_run["status"]
        ).upper()

        st.caption(
            "LATEST PIPELINE RUN"
        )

        if status == "SUCCESS":

            st.success(
                "SUCCESS",
                icon="✅",
            )

        elif status == "RUNNING":

            st.warning(
                "RUNNING",
                icon="⏳",
            )

        else:

            st.error(
                "FAILED",
                icon="❌",
            )

        st.caption(
            str(
                sidebar_run["started_at"]
            )
        )

    st.divider()

    st.caption(
        "PostgreSQL analytical warehouse"
    )


# ============================================================
# FILTER DATA
# ============================================================

weather_filtered = weather.copy()


if (
    selected_asset != "All Assets"
    and not weather.empty
):
    weather_filtered = (
        weather[
            weather["asset_name"]
            == selected_asset
        ]
        .copy()
    )


assets_filtered = assets.copy()


if (
    selected_asset != "All Assets"
    and not assets.empty
):
    assets_filtered = (
        assets[
            assets["asset_name"]
            == selected_asset
        ]
        .copy()
    )


critical_filtered = critical.copy()


if (
    selected_asset != "All Assets"
    and not critical.empty
):
    critical_filtered = (
        critical[
            critical["asset_name"]
            == selected_asset
        ]
        .copy()
    )


# ============================================================
# EXECUTIVE PAGE
# ============================================================

if page == "Executive":

    hero(
        "Executive Operations Center",
        "Oil & Gas Operations Intelligence",
        (
            "Integrated offshore weather risk, "
            "marine forecasting, rig-market activity, "
            "energy data and warehouse intelligence."
        ),
    )

    if executive.empty:
        st.error(
            "Executive view returned no data."
        )
        st.stop()

    kpi = executive.iloc[0]

    st.html(
        f"""
        <div class="freshness-bar">

            Forecast run:
            <b>
                {kpi['weather_forecast_reference_time']}
            </b>

            &nbsp;&nbsp; | &nbsp;&nbsp;

            Rig data:
            <b>
                {kpi['rig_count_date']}
            </b>

            &nbsp;&nbsp; | &nbsp;&nbsp;

            Energy data:
            <b>
                {kpi['energy_price_date']}
            </b>

        </div>
        """
    )

    section_header(
        "Business Overview",
        "Executive Snapshot",
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        kpi_card(
            "Latest Rig Count",
            f"{kpi['total_rig_count']:,.0f}",
            (
                f"{kpi['countries_reporting']:,.0f} "
                "reporting countries"
            ),
        )

    with c2:

        kpi_card(
            "Energy Price",
            f"${kpi['average_energy_price_usd']:,.2f}",
            "Latest warehouse observation",
        )

    with c3:

        kpi_card(
            "Monitored Assets",
            f"{kpi['monitored_assets']:,.0f}",
            "Active offshore assets",
        )

    with c4:

        red_pct = float(
            kpi["red_hours_percent"]
        )

        exposure_status = (
            "RED"
            if red_pct > 10
            else (
                "AMBER"
                if red_pct > 0
                else "GREEN"
            )
        )

        kpi_card(
            "Operational Exposure",
            f"{red_pct:.1f}%",
            "Forecast hours classified RED",
            status=exposure_status,
        )

    st.write("")

    c1, c2, c3 = st.columns(3)

    with c1:

        kpi_card(
            "Green Hours",
            f"{kpi['green_hours_percent']:.1f}%",
            "Conditions within limits",
            status="GREEN",
        )

    with c2:

        kpi_card(
            "Amber Hours",
            f"{kpi['amber_hours_percent']:.1f}%",
            "Enhanced monitoring",
            status="AMBER",
        )

    with c3:

        kpi_card(
            "Red Hours",
            f"{kpi['red_hours_percent']:.1f}%",
            "Operational restrictions",
            status="RED",
        )

    st.write("")

    section_header(
        "Operational Risk",
        "Asset Availability",
    )

    if not assets_filtered.empty:

        availability = (
            assets_filtered.melt(
                id_vars=[
                    "asset_name"
                ],
                value_vars=[
                    "green_hours",
                    "amber_hours",
                    "red_hours",
                ],
                var_name="risk",
                value_name="hours",
            )
        )

        availability["risk"] = (
            availability["risk"]
            .str.replace(
                "_hours",
                "",
            )
            .str.upper()
        )

        fig = px.bar(
            availability,

            x="asset_name",
            y="hours",
            color="risk",

            barmode="stack",

            color_discrete_map={
                "GREEN": "#22c55e",
                "AMBER": "#f59e0b",
                "RED": "#ef4444",
            },

            labels={
                "asset_name": "",
                "hours": "Forecast Hours",
                "risk": "Risk Level",
            },

            title=(
                "Forecast Operational Availability "
                "by Asset"
            ),
        )

        style_chart(
            fig,
            420,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    left, right = st.columns(
        [1.35, 1]
    )

    with left:

        section_header(
            "Market",
            "Global Rig Activity",
        )

        if not rig.empty:

            rig_fig = px.line(
                rig,

                x="date",
                y="rig_count",
                color="region",

                labels={
                    "date": "",
                    "rig_count": "Rig Count",
                    "region": "Region",
                },

                title=(
                    "Monthly Rig Activity "
                    "by Region"
                ),
            )

            style_chart(
                rig_fig,
                390,
            )

            st.plotly_chart(
                rig_fig,
                width="stretch",
            )

    with right:

        section_header(
            "Forward Risk",
            "Critical Events",
        )

        if critical_filtered.empty:

            st.success(
                "No Amber or Red events "
                "currently forecast."
            )

        else:

            display = (
                critical_filtered[
                    [
                        "asset_name",
                        "forecast_valid_time",
                        "overall_risk_level",
                        "limiting_parameter",
                    ]
                ]
                .copy()
            )

            st.dataframe(
                display,
                hide_index=True,
                width="stretch",
                height=330,
            )


# ============================================================
# OFFSHORE OPERATIONS
# ============================================================

elif page == "Offshore Operations":

    hero(
        "Marine Operations",
        "Offshore Weather Operations",
        (
            "Atmospheric and marine forecast "
            "intelligence designed for offshore "
            "operational decision support."
        ),
    )

    if weather_filtered.empty:

        st.warning(
            "No weather records available."
        )

        st.stop()

    forecast = weather_filtered.copy()

    section_header(
        "Forecast Risk",
        "Operational Status",
    )

    red_hours = int(
        forecast[
            "overall_risk_level"
        ]
        .eq("RED")
        .sum()
    )

    amber_hours = int(
        forecast[
            "overall_risk_level"
        ]
        .eq("AMBER")
        .sum()
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        kpi_card(
            "Maximum Gust",
            (
                f"{forecast['wind_gust_kmh'].max():.1f} "
                "km/h"
            ),
            "Highest forecast gust",
        )

    with c2:

        kpi_card(
            "Maximum Wave",
            (
                f"{forecast['wave_height_m'].max():.2f} m"
            ),
            "Significant wave height",
        )

    with c3:

        kpi_card(
            "Minimum Visibility",
            (
                f"{forecast['visibility_m'].min():,.0f} m"
            ),
            "Lowest forecast visibility",
        )

    with c4:

        status = (
            "RED"
            if red_hours > 0
            else (
                "AMBER"
                if amber_hours > 0
                else "GREEN"
            )
        )

        kpi_card(
            "Operational Exposure",
            status,
            (
                f"{red_hours} RED / "
                f"{amber_hours} AMBER hours"
            ),
            status=status,
        )

    st.write("")

    (
        tab_wind,
        tab_wave,
        tab_visibility,
        tab_risk,
    ) = st.tabs(
        [
            "Wind",
            "Waves",
            "Visibility",
            "Risk Timeline",
        ]
    )

    with tab_wind:

        fig = px.line(
            forecast,

            x="forecast_valid_time",

            y=[
                "wind_speed_kmh",
                "wind_gust_kmh",
            ],

            labels={
                "forecast_valid_time": "",
                "value": "km/h",
                "variable": "",
            },

            title=(
                "Wind Speed & Gust Forecast"
            ),
        )

        style_chart(
            fig,
            450,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    with tab_wave:

        fig = px.line(
            forecast,

            x="forecast_valid_time",

            y=[
                "wave_height_m",
                "swell_wave_height_m",
            ],

            labels={
                "forecast_valid_time": "",
                "value": "Height (m)",
                "variable": "",
            },

            title=(
                "Wave & Swell Forecast"
            ),
        )

        style_chart(
            fig,
            450,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    with tab_visibility:

        fig = px.line(
            forecast,

            x="forecast_valid_time",
            y="visibility_m",
            color="asset_name",

            labels={
                "forecast_valid_time": "",
                "visibility_m": "Visibility (m)",
                "asset_name": "Asset",
            },

            title="Forecast Visibility",
        )

        style_chart(
            fig,
            450,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    with tab_risk:

        risk_counts = (
            forecast
            .groupby(
                [
                    "forecast_valid_time",
                    "overall_risk_level",
                ],
                as_index=False,
            )
            .size()
        )

        fig = px.scatter(
            risk_counts,

            x="forecast_valid_time",
            y="overall_risk_level",

            size="size",
            color="overall_risk_level",

            color_discrete_map={
                "GREEN": "#22c55e",
                "AMBER": "#f59e0b",
                "RED": "#ef4444",
                "UNKNOWN": "#94a3b8",
            },

            labels={
                "forecast_valid_time": "",
                "overall_risk_level": "Risk",
                "size": "Assets",
            },

            title=(
                "Operational Risk Timeline"
            ),
        )

        style_chart(
            fig,
            420,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    section_header(
        "Export",
        "Operational Forecast Dataset",
    )

    st.download_button(
        "Download forecast CSV",
        data=csv_bytes(
            forecast
        ),
        file_name=(
            "offshore_weather_forecast.csv"
        ),
        mime="text/csv",
    )


# ============================================================
# RIG MARKET
# ============================================================

elif page == "Rig Market":

    hero(
        "Market Intelligence",
        "Global Rig Market",
        (
            "Baker Hughes drilling activity "
            "across regions and historical "
            "reporting periods."
        ),
    )

    if rig.empty:

        st.warning(
            "No rig data available."
        )

        st.stop()

    rig = rig.copy()

    rig["date"] = pd.to_datetime(
        rig["date"],
        errors="coerce",
    )

    latest_date = (
        rig["date"].max()
    )

    latest_rig = (
        rig[
            rig["date"]
            == latest_date
        ]
        .copy()
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        kpi_card(
            "Reporting Month",
            latest_date.strftime(
                "%b %Y"
            ),
            "Latest reporting period",
        )

    with c2:

        kpi_card(
            "Latest Rig Activity",
            (
                f"{latest_rig['rig_count'].sum():,.0f}"
            ),
            "Latest regional observations",
        )

    with c3:

        kpi_card(
            "Regions",
            (
                f"{latest_rig['region'].nunique()}"
            ),
            "Regions represented",
        )

    fig = px.line(
        rig,

        x="date",
        y="rig_count",
        color="region",

        title=(
            "Rig Count Evolution by Region"
        ),

        labels={
            "date": "",
            "rig_count": "Rig Count",
            "region": "Region",
        },
    )

    style_chart(
        fig,
        480,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    region_latest = (
        latest_rig
        .groupby(
            "region",
            as_index=False,
        )["rig_count"]
        .sum()
    )

    fig = px.bar(
        region_latest,

        x="region",
        y="rig_count",

        title=(
            "Latest Rig Activity by Region"
        ),

        labels={
            "region": "",
            "rig_count": "Rig Count",
        },
    )

    style_chart(
        fig,
        410,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.download_button(
        "Download rig market CSV",
        data=csv_bytes(
            rig
        ),
        file_name="rig_market.csv",
        mime="text/csv",
    )


# ============================================================
# ENERGY INTELLIGENCE
# ============================================================

elif page == "Energy Intelligence":

    hero(
        "Energy Market",
        "Energy Price Intelligence",
        (
            "EIA energy-price observations "
            "integrated into the analytical "
            "PostgreSQL warehouse."
        ),
    )

    if not executive.empty:

        kpi = executive.iloc[0]

        c1, c2, c3 = st.columns(3)

        with c1:

            kpi_card(
                "Average Price",
                (
                    f"${kpi['average_energy_price_usd']:,.2f}"
                ),
                "Latest warehouse observation",
            )

        with c2:

            kpi_card(
                "Price Date",
                str(
                    kpi["energy_price_date"]
                ),
                "Latest reporting date",
            )

        with c3:

            kpi_card(
                "Observations",
                (
                    f"{kpi['energy_price_observations']:,.0f}"
                ),
                "Latest reporting period",
            )

    st.write("")

    if not energy.empty:

        price_column = None

        for candidate in (
            "average_price_usd",
            "price_usd",
            "price",
        ):
            if candidate in energy.columns:
                price_column = candidate
                break

        if (
            price_column
            and "date" in energy.columns
        ):

            fig = px.line(
                energy,

                x="date",
                y=price_column,

                color=(
                    "product"
                    if "product"
                    in energy.columns
                    else None
                ),

                title=(
                    "Historical Energy Price"
                ),

                labels={
                    "date": "",
                    price_column: "USD",
                    "product": "Product",
                },
            )

            style_chart(
                fig,
                480,
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        st.info(
            "The current EIA dataset represents "
            "a refined-product price series. "
            "It is intentionally presented as "
            "Energy Price Intelligence rather "
            "than WTI crude oil."
        )

        st.download_button(
            "Download energy price CSV",
            data=csv_bytes(
                energy
            ),
            file_name=(
                "energy_prices.csv"
            ),
            mime="text/csv",
        )


# ============================================================
# DATA QUALITY
# ============================================================

elif page == "Data Quality":

    hero(
        "Platform Reliability",
        "Data Quality & Pipeline Health",
        (
            "Live pipeline observability, "
            "validation results and warehouse "
            "health stored in PostgreSQL."
        ),
    )

    section_header(
        "Orchestration",
        "Latest Pipeline Execution",
    )

    if pipeline_run.empty:

        st.warning(
            "No pipeline executions found."
        )

    else:

        latest_run = (
            pipeline_run.iloc[0]
        )

        status = str(
            latest_run["status"]
        ).upper()

        status_level = {
            "SUCCESS": "GREEN",
            "RUNNING": "AMBER",
            "FAILED": "RED",
        }.get(
            status,
            "RED",
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            kpi_card(
                "Pipeline Status",
                status,
                (
                    f"Run #"
                    f"{latest_run['pipeline_run_key']}"
                ),
                status=status_level,
            )

        with c2:

            duration = (
                latest_run[
                    "duration_seconds"
                ]
            )

            duration_text = (
                "Running"
                if pd.isna(duration)
                else f"{float(duration):.1f} s"
            )

            kpi_card(
                "Duration",
                duration_text,
                "Total execution time",
            )

        with c3:

            kpi_card(
                "Started",
                str(
                    latest_run[
                        "started_at"
                    ]
                )[:19],
                "Pipeline start time",
            )

        with c4:

            finished = (
                latest_run[
                    "finished_at"
                ]
            )

            kpi_card(
                "Finished",
                (
                    str(finished)[:19]
                    if pd.notna(finished)
                    else "Running"
                ),
                "Pipeline completion time",
            )

        if (
            status == "FAILED"
            and pd.notna(
                latest_run[
                    "error_message"
                ]
            )
        ):
            st.error(
                str(
                    latest_run[
                        "error_message"
                    ]
                )
            )

    st.write("")

    section_header(
        "Validation",
        "Warehouse Quality",
    )

    if quality_summary.empty:

        st.warning(
            "No quality results found."
        )

    else:

        q = quality_summary.iloc[0]

        total_checks = int(
            q["total_checks"]
        )

        passed_checks = int(
            q["passed_checks"]
        )

        failed_checks = int(
            q["failed_checks"]
        )

        pass_rate = float(
            q["pass_rate_percent"]
            or 0
        )

        quality_status = (
            "GREEN"
            if failed_checks == 0
            else (
                "AMBER"
                if pass_rate >= 90
                else "RED"
            )
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            kpi_card(
                "Quality Checks",
                (
                    f"{passed_checks} / "
                    f"{total_checks}"
                ),
                "Checks passed",
                status=quality_status,
            )

        with c2:

            kpi_card(
                "Pass Rate",
                f"{pass_rate:.1f}%",
                "Latest validation run",
                status=quality_status,
            )

        with c3:

            kpi_card(
                "Failed Checks",
                str(
                    failed_checks
                ),
                "Validation failures",
                status=(
                    "GREEN"
                    if failed_checks == 0
                    else "RED"
                ),
            )

        with c4:

            kpi_card(
                "Warehouse Health",
                (
                    "HEALTHY"
                    if failed_checks == 0
                    else "ATTENTION"
                ),
                "Derived from validation",
                status=quality_status,
            )

    st.write("")

    section_header(
        "Validation Details",
        "Individual Quality Checks",
    )

    if not quality_checks.empty:

        display = (
            quality_checks.copy()
        )

        display["status"] = (
            display["passed"]
            .map(
                {
                    True: "PASS",
                    False: "FAIL",
                }
            )
        )

        wanted_columns = [
            column
            for column in [
                "status",
                "check_name",
                "check_value",
                "expectation",
                "details",
                "checked_at",
            ]
            if column
            in display.columns
        ]

        display = display[
            wanted_columns
        ]

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            height=500,
        )

        st.download_button(
            "Download quality report CSV",
            data=csv_bytes(
                display
            ),
            file_name=(
                "data_quality_report.csv"
            ),
            mime="text/csv",
        )

    st.write("")

    section_header(
        "Observability",
        "Pipeline Execution History",
    )

    if not pipeline_history.empty:

        history = (
            pipeline_history.copy()
        )

        history["started_at"] = (
            pd.to_datetime(
                history["started_at"],
                errors="coerce",
            )
        )

        history_columns = [
            column
            for column in [
                "pipeline_run_key",
                "started_at",
                "duration_seconds",
                "status",
                "total_checks",
                "passed_checks",
                "failed_checks",
                "error_message",
            ]
            if column
            in history.columns
        ]

        st.dataframe(
            history[
                history_columns
            ],
            width="stretch",
            hide_index=True,
        )

        successful = (
            history[
                history["status"]
                == "SUCCESS"
            ]
            .copy()
        )

        if not successful.empty:

            fig = px.bar(
                successful,

                x="started_at",
                y="duration_seconds",

                title=(
                    "Pipeline Execution Duration"
                ),

                labels={
                    "started_at":
                        "Pipeline Run",
                    "duration_seconds":
                        "Duration (seconds)",
                },
            )

            style_chart(
                fig,
                400,
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

    st.write("")

    section_header(
        "Warehouse",
        "Fact Table Volume",
    )

    if not warehouse_volume.empty:

        st.dataframe(
            warehouse_volume,
            width="stretch",
            hide_index=True,
        )

        fig = px.bar(
            warehouse_volume,

            x="dataset",
            y="row_count",

            title=(
                "Operational Warehouse Volume"
            ),

            labels={
                "dataset": "",
                "row_count": "Rows",
            },
        )

        style_chart(
            fig,
            400,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )


# ============================================================
# FOOTER
# ============================================================

st.html(
    """
    <div style="
        margin-top:48px;
        padding-top:18px;

        border-top:
            1px solid
            rgba(148,163,184,0.10);

        color:#64748b;
        font-size:11px;

        display:flex;
        justify-content:space-between;
    ">

        <span>
            Oil & Gas Data Engineering Platform
        </span>

        <span>
            Python · PostgreSQL · Streamlit · Plotly
        </span>

    </div>
    """
)