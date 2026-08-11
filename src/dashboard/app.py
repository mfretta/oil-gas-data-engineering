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
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.html(
    """
    <style>

    .stApp {
        background:
            linear-gradient(
                180deg,
                #07111f 0%,
                #0b1626 55%,
                #0d1828 100%
            );
        color: #f8fafc;
    }

    html, body {
        font-family:
            Inter,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1650px;
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #07101d,
                #0a1422
            );

        border-right:
            1px solid rgba(255,255,255,0.08);
    }

    .hero {
        padding: 28px 30px;

        border-radius: 20px;

        background:
            radial-gradient(
                circle at top right,
                rgba(14,165,233,0.23),
                transparent 36%
            ),
            linear-gradient(
                135deg,
                rgba(15,23,42,0.98),
                rgba(17,34,54,0.96)
            );

        border:
            1px solid rgba(148,163,184,0.18);

        box-shadow:
            0 18px 50px rgba(0,0,0,0.22);

        margin-bottom: 24px;
    }

    .hero-eyebrow {
        color: #38bdf8;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.7px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .hero-title {
        color: #f8fafc;
        font-size: 36px;
        font-weight: 760;
        letter-spacing: -0.8px;
        margin-bottom: 8px;
    }

    .hero-description {
        color: #94a3b8;
        font-size: 15px;
        line-height: 1.6;
        max-width: 980px;
    }

    .section-label {
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        font-size: 11px;
        font-weight: 700;
        margin-top: 17px;
        margin-bottom: 5px;
    }

    .section-title {
        color: #f8fafc;
        font-size: 23px;
        font-weight: 700;
        margin-bottom: 18px;
    }

    .kpi-card {
        min-height: 142px;

        padding: 21px;

        border-radius: 17px;

        background:
            linear-gradient(
                145deg,
                rgba(20,32,49,0.96),
                rgba(14,25,40,0.98)
            );

        border:
            1px solid rgba(148,163,184,0.12);

        box-shadow:
            0 8px 30px rgba(0,0,0,0.18);
    }

    .kpi-label {
        color: #94a3b8;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.7px;
        margin-bottom: 13px;
    }

    .kpi-value {
        color: #f8fafc;
        font-size: 31px;
        line-height: 1;
        font-weight: 760;
        margin-bottom: 13px;
    }

    .kpi-note {
        color: #64748b;
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
        color: #4ade80;
    }

    .amber-text {
        color: #fbbf24;
    }

    .red-text {
        color: #f87171;
    }

    .freshness-bar {
        padding: 12px 18px;

        border-radius: 12px;

        background:
            rgba(15,27,43,0.9);

        border:
            1px solid rgba(148,163,184,0.12);

        color: #94a3b8;

        font-size: 12px;

        margin-bottom: 20px;
    }

    [data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;

        border:
            1px solid rgba(148,163,184,0.12);
    }

    hr {
        border-color:
            rgba(148,163,184,0.10);
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    header {
        background: transparent;
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

        st.caption(str(error))

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


quality = safe_query(
    """
    SELECT
        'Atmospheric Forecast' AS dataset,
        COUNT(*) AS row_count,
        MAX(forecast_reference_time)
            AS latest_update
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
    "Warehouse volume data",
)


pipeline_run = safe_query(
    """
    SELECT
        pipeline_run_key,
        pipeline_name,
        started_at,
        finished_at,
        duration_seconds,
        status,
        error_message
    FROM vw_latest_pipeline_run;
    """,
    "Latest pipeline run",
)


quality_summary = safe_query(
    """
    SELECT
        pipeline_run_key,
        total_checks,
        passed_checks,
        failed_checks,
        pass_rate_percent
    FROM vw_latest_quality_summary;
    """,
    "Latest quality summary",
)


quality_checks = safe_query(
    """
    SELECT
        quality_check_key,
        pipeline_run_key,
        check_name,
        passed,
        check_value,
        expectation,
        details,
        checked_at
    FROM vw_latest_quality_checks
    ORDER BY
        passed ASC,
        check_name;
    """,
    "Latest quality checks",
)


pipeline_history = safe_query(
    """
    SELECT
        pipeline_run_key,
        pipeline_name,
        started_at,
        finished_at,
        duration_seconds,
        status,
        error_message,
        total_checks,
        passed_checks,
        failed_checks
    FROM vw_pipeline_run_history
    ORDER BY started_at DESC
    LIMIT 20;
    """,
    "Pipeline run history",
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
            color="#cbd5e1",
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
            font-size:24px;
            font-weight:750;
            color:#f8fafc;
            margin-bottom:3px;
        ">
            ◈ O&G Intelligence
        </div>

        <div style="
            color:#64748b;
            font-size:12px;
            margin-bottom:24px;
        ">
            Operations Data Platform
        </div>
        """
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
        latest_sidebar_run = (
            pipeline_run.iloc[0]
        )

        st.caption(
            "Latest pipeline run"
        )

        st.write(
            f"**{latest_sidebar_run['status']}**"
        )

        st.caption(
            str(
                latest_sidebar_run[
                    "started_at"
                ]
            )
        )

    st.caption(
        "PostgreSQL analytical warehouse"
    )


# ============================================================
# WEATHER FILTER
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


# ============================================================
# EXECUTIVE
# ============================================================

if page == "Executive":

    hero(
        "Executive Operations Center",

        "Oil & Gas Operations Intelligence",

        (
            "Integrated offshore weather risk, marine "
            "forecasting, rig-market activity, energy data "
            "and warehouse intelligence."
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
            <b>{kpi['weather_forecast_reference_time']}</b>

            &nbsp;&nbsp; | &nbsp;&nbsp;

            Rig data:
            <b>{kpi['rig_count_date']}</b>

            &nbsp;&nbsp; | &nbsp;&nbsp;

            Energy data:
            <b>{kpi['energy_price_date']}</b>

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

        if red_pct > 10:
            exposure_status = "RED"

        elif red_pct > 0:
            exposure_status = "AMBER"

        else:
            exposure_status = "GREEN"

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

    if not assets.empty:

        availability = assets.melt(
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
                "GREEN":
                    "#22c55e",

                "AMBER":
                    "#f59e0b",

                "RED":
                    "#ef4444",
            },

            labels={
                "asset_name":
                    "",

                "hours":
                    "Forecast Hours",

                "risk":
                    "Risk Level",
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
        [1.4, 1]
    )

    with left:

        section_header(
            "Market",
            "Global Rig Activity",
        )

        if not rig.empty:

            rig_chart = px.line(
                rig,

                x="date",

                y="rig_count",

                color="region",

                labels={
                    "date":
                        "",

                    "rig_count":
                        "Rig Count",

                    "region":
                        "Region",
                },

                title=(
                    "Monthly Rig Activity "
                    "by Region"
                ),
            )

            style_chart(
                rig_chart,
                390,
            )

            st.plotly_chart(
                rig_chart,
                width="stretch",
            )

    with right:

        section_header(
            "Forward Risk",
            "Critical Events",
        )

        if critical.empty:

            st.success(
                "No Amber or Red events currently forecast."
            )

        else:

            critical_display = (
                critical[
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
                critical_display,

                width="stretch",

                hide_index=True,

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
            "Detailed atmospheric and marine forecast "
            "intelligence for offshore operational "
            "decision support."
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

    red_hours = (
        forecast[
            "overall_risk_level"
        ]
        .eq("RED")
        .sum()
    )

    amber_hours = (
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
            "Current Exposure",

            status,

            (
                f"{red_hours} RED / "
                f"{amber_hours} AMBER hours"
            ),

            status=status,
        )

    st.write("")

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Wind",
            "Waves",
            "Visibility",
            "Risk Timeline",
        ]
    )

    with tab1:

        fig = px.line(
            forecast,

            x="forecast_valid_time",

            y=[
                "wind_speed_kmh",
                "wind_gust_kmh",
            ],

            labels={
                "forecast_valid_time":
                    "",

                "value":
                    "km/h",

                "variable":
                    "",
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

    with tab2:

        fig = px.line(
            forecast,

            x="forecast_valid_time",

            y=[
                "wave_height_m",
                "swell_wave_height_m",
            ],

            labels={
                "forecast_valid_time":
                    "",

                "value":
                    "Height (m)",

                "variable":
                    "",
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

    with tab3:

        fig = px.line(
            forecast,

            x="forecast_valid_time",

            y="visibility_m",

            color="asset_name",

            labels={
                "forecast_valid_time":
                    "",

                "visibility_m":
                    "Visibility (m)",

                "asset_name":
                    "Asset",
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

    with tab4:

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

        risk_fig = px.scatter(
            risk_counts,

            x="forecast_valid_time",

            y="overall_risk_level",

            size="size",

            color="overall_risk_level",

            color_discrete_map={
                "GREEN":
                    "#22c55e",

                "AMBER":
                    "#f59e0b",

                "RED":
                    "#ef4444",

                "UNKNOWN":
                    "#94a3b8",
            },

            labels={
                "forecast_valid_time":
                    "",

                "overall_risk_level":
                    "Risk",

                "size":
                    "Assets",
            },

            title=(
                "Operational Risk Timeline"
            ),
        )

        style_chart(
            risk_fig,
            420,
        )

        st.plotly_chart(
            risk_fig,
            width="stretch",
        )

    section_header(
        "Export",
        "Operational Forecast Data",
    )

    st.download_button(
        label="Download forecast CSV",

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
            "Baker Hughes drilling activity across "
            "regions, countries and operational categories."
        ),
    )

    if rig.empty:

        st.warning(
            "No rig data available."
        )

        st.stop()

    rig["date"] = pd.to_datetime(
        rig["date"],
        errors="coerce",
    )

    latest_date = rig[
        "date"
    ].max()

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

            "Latest rig-count period",
        )

    with c2:

        kpi_card(
            "Latest Rig Activity",

            (
                f"{latest_rig['rig_count'].sum():,.0f}"
            ),

            "Latest reporting records",
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
            "date":
                "",

            "rig_count":
                "Rig Count",

            "region":
                "Region",
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
            "Latest Rig Activity "
            "by Region"
        ),
    )

    style_chart(
        fig,
        400,
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

        file_name=
            "rig_market.csv",

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
            "Energy-market observations from the EIA "
            "pipeline integrated with the operational "
            "data warehouse."
        ),
    )

    if not executive.empty:

        kpi = executive.iloc[0]

        c1, c2, c3 = st.columns(3)

        with c1:

            kpi_card(
                "Average Price",

                f"${kpi['average_energy_price_usd']:,.2f}",

                "Latest available observation",
            )

        with c2:

            kpi_card(
                "Price Date",

                str(
                    kpi[
                        "energy_price_date"
                    ]
                ),

                "Latest reporting date",
            )

        with c3:

            kpi_card(
                "Observations",

                (
                    f"{kpi['energy_price_observations']:,.0f}"
                ),

                "Latest period",
            )

    if not energy.empty:

        price_column = None

        for column in [
            "price_usd",
            "average_price_usd",
            "price",
        ]:

            if column in energy.columns:

                price_column = column

                break

        if (
            price_column is not None
            and "date"
            in energy.columns
        ):

            fig = px.line(
                energy,

                x="date",

                y=price_column,

                title=(
                    "Historical Energy Price"
                ),

                labels={
                    "date":
                        "",

                    price_column:
                        "USD",
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

        st.download_button(
            "Download energy price CSV",

            data=csv_bytes(
                energy
            ),

            file_name=
                "energy_prices.csv",

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
            "Live observability from PostgreSQL showing "
            "pipeline executions, validation results, "
            "warehouse volume and operational reliability."
        ),
    )

    # --------------------------------------------------------
    # PIPELINE RUN
    # --------------------------------------------------------

    section_header(
        "Orchestration",
        "Latest Pipeline Execution",
    )

    if pipeline_run.empty:

        st.warning(
            "No pipeline execution records found."
        )

    else:

        latest_run = (
            pipeline_run.iloc[0]
        )

        pipeline_status = str(
            latest_run[
                "status"
            ]
        ).upper()

        if pipeline_status == "SUCCESS":

            status_level = "GREEN"

        elif pipeline_status == "RUNNING":

            status_level = "AMBER"

        else:

            status_level = "RED"

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            kpi_card(
                "Pipeline Status",

                pipeline_status,

                (
                    "Run #"
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

            if pd.isna(duration):

                duration_text = "Running"

            else:

                duration_text = (
                    f"{float(duration):.1f} s"
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

            finished_at = (
                latest_run[
                    "finished_at"
                ]
            )

            finished_text = (
                str(finished_at)[:19]
                if pd.notna(
                    finished_at
                )
                else "Running"
            )

            kpi_card(
                "Finished",

                finished_text,

                "Pipeline completion time",
            )

        if (
            pipeline_status == "FAILED"
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

    # --------------------------------------------------------
    # QUALITY SUMMARY
    # --------------------------------------------------------

    st.write("")

    section_header(
        "Validation",
        "Warehouse Quality",
    )

    if quality_summary.empty:

        st.warning(
            "No persisted data-quality results "
            "for the latest pipeline run."
        )

    else:

        q = quality_summary.iloc[0]

        total_checks = int(
            q[
                "total_checks"
            ]
        )

        passed_checks = int(
            q[
                "passed_checks"
            ]
        )

        failed_checks = int(
            q[
                "failed_checks"
            ]
        )

        pass_rate = float(
            q[
                "pass_rate_percent"
            ]
            or 0
        )

        if failed_checks == 0:

            quality_status = "GREEN"

        elif pass_rate >= 90:

            quality_status = "AMBER"

        else:

            quality_status = "RED"

        q1, q2, q3, q4 = st.columns(4)

        with q1:

            kpi_card(
                "Quality Checks",

                (
                    f"{passed_checks} / "
                    f"{total_checks}"
                ),

                "Checks passed",

                status=
                    quality_status,
            )

        with q2:

            kpi_card(
                "Pass Rate",

                f"{pass_rate:.1f}%",

                "Latest validation run",

                status=
                    quality_status,
            )

        with q3:

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

        with q4:

            kpi_card(
                "Warehouse Health",

                (
                    "HEALTHY"
                    if failed_checks == 0
                    else "ATTENTION"
                ),

                "Derived from live validation",

                status=
                    quality_status,
            )

    # --------------------------------------------------------
    # QUALITY CHECK DETAILS
    # --------------------------------------------------------

    st.write("")

    section_header(
        "Validation Details",
        "Individual Quality Checks",
    )

    if not quality_checks.empty:

        checks_display = (
            quality_checks[
                [
                    "check_name",
                    "passed",
                    "check_value",
                    "expectation",
                    "details",
                    "checked_at",
                ]
            ]
            .copy()
        )

        checks_display[
            "status"
        ] = checks_display[
            "passed"
        ].map(
            {
                True:
                    "PASS",

                False:
                    "FAIL",
            }
        )

        checks_display = (
            checks_display[
                [
                    "status",
                    "check_name",
                    "check_value",
                    "expectation",
                    "details",
                    "checked_at",
                ]
            ]
        )

        st.dataframe(
            checks_display,

            width="stretch",

            hide_index=True,

            height=500,
        )

        st.download_button(
            label=(
                "Download quality report CSV"
            ),

            data=csv_bytes(
                checks_display
            ),

            file_name=(
                "data_quality_report.csv"
            ),

            mime="text/csv",
        )

    # --------------------------------------------------------
    # PIPELINE HISTORY
    # --------------------------------------------------------

    st.write("")

    section_header(
        "Observability",
        "Pipeline Execution History",
    )

    if not pipeline_history.empty:

        history = (
            pipeline_history.copy()
        )

        history[
            "started_at"
        ] = pd.to_datetime(
            history[
                "started_at"
            ],

            errors="coerce",
        )

        st.dataframe(
            history[
                [
                    "pipeline_run_key",
                    "started_at",
                    "duration_seconds",
                    "status",
                    "total_checks",
                    "passed_checks",
                    "failed_checks",
                    "error_message",
                ]
            ],

            width="stretch",

            hide_index=True,
        )

        successful_runs = (
            history[
                history[
                    "status"
                ]
                == "SUCCESS"
            ]
        )

        if not successful_runs.empty:

            duration_chart = px.bar(
                successful_runs,

                x="started_at",

                y="duration_seconds",

                labels={
                    "started_at":
                        "Pipeline Run",

                    "duration_seconds":
                        "Duration (seconds)",
                },

                title=(
                    "Pipeline Execution Duration"
                ),
            )

            style_chart(
                duration_chart,
                400,
            )

            st.plotly_chart(
                duration_chart,

                width="stretch",
            )

    # --------------------------------------------------------
    # WAREHOUSE VOLUME
    # --------------------------------------------------------

    st.write("")

    section_header(
        "Warehouse",
        "Fact Table Volume",
    )

    if not quality.empty:

        st.dataframe(
            quality,

            width="stretch",

            hide_index=True,
        )

        volume_chart = px.bar(
            quality,

            x="dataset",

            y="row_count",

            labels={
                "dataset":
                    "",

                "row_count":
                    "Rows",
            },

            title=(
                "Operational Warehouse Volume"
            ),
        )

        style_chart(
            volume_chart,
            400,
        )

        st.plotly_chart(
            volume_chart,

            width="stretch",
        )


# ============================================================
# FOOTER
# ============================================================

st.html(
    """
    <div style="
        margin-top:45px;
        padding-top:18px;

        border-top:
            1px solid rgba(148,163,184,0.10);

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