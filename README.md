# Oil & Gas Data Engineering Platform

End-to-end data engineering platform for **offshore energy operations**, combining atmospheric forecasts, marine conditions, drilling activity, energy pricing, operational risk, data quality, and pipeline observability.

Built with **Python, SQL, PostgreSQL, Parquet, Docker, Streamlit, and Plotly**.

---

# Project

## Offshore Energy Data Platform

Multi-source data pipeline transforming weather, marine, energy-price, and rig-count data into a dimensional PostgreSQL warehouse and operational analytics layer.

**Skills:** Python ETL, SQL, dimensional modeling, REST APIs, Parquet, PostgreSQL, Docker, data quality, observability, geospatial analytics

### Key Outcomes

- ✅ Open-Meteo atmospheric and marine ingestion
- ✅ Baker Hughes Worldwide Rig Count ingestion
- ✅ EIA energy-price ingestion
- ✅ Bronze raw-data layer
- ✅ Silver Parquet layer
- ✅ PostgreSQL dimensional warehouse
- ✅ Asset-specific operational weather risk
- ✅ Analytical SQL views
- ✅ 22 automated data-quality checks
- ✅ Pipeline observability
- ✅ Interactive offshore asset map
- ✅ Streamlit operational dashboard
- ✅ Reproducible Docker Compose environment

---

# Architecture

![Oil & Gas Data Engineering Architecture](docs/images/architecture.png)

### Engineering Flow

```text
Open-Meteo Atmospheric API ─┐
Open-Meteo Marine API ──────┤
EIA Energy API ─────────────┼──► Python Ingestion
Baker Hughes Rig Count ─────┘
                                   │
                                   ▼
                           Bronze Raw Layer
                           JSON / Excel
                                   │
                                   ▼
                           Silver Data Layer
                              Parquet
                                   │
                                   ▼
                      PostgreSQL Data Warehouse
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
         Weather Facts        Energy Facts        Rig Count Facts
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   ▼
                         Analytical SQL Views
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
             Data Quality                  Observability
              22 Checks                   Pipeline Runs
                    │                             │
                    └──────────────┬──────────────┘
                                   ▼
                         Streamlit Dashboard
                                   │
                                   ▼
                      Geospatial Decision Support