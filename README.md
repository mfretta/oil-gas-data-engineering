# Oil & Gas Data Engineering Platform

An end-to-end Data Engineering portfolio project integrating offshore weather, marine conditions, energy prices, rig activity, PostgreSQL analytics, operational risk logic, data quality, observability, and a Streamlit frontend.

The project demonstrates how heterogeneous operational and market data can be ingested, transformed, modeled, validated, monitored, and exposed through analytical views and dashboards.

---

## Project Objectives

This project was designed to simulate a realistic Oil & Gas data platform capable of supporting:

- Offshore operational weather monitoring
- Marine-condition awareness
- Operational weather-risk classification
- Global drilling activity analysis
- Energy-price intelligence
- Dimensional warehouse modeling
- Automated data-quality validation
- Pipeline observability
- Executive and operational dashboards

---

## Architecture

```text
Open-Meteo Atmospheric API ──┐
Open-Meteo Marine API ───────┤
EIA API ─────────────────────┼──► Bronze Layer
Baker Hughes Workbook ───────┘
                                  │
                                  ▼
                            Silver Layer
                              Parquet
                                  │
                                  ▼
                             PostgreSQL
                           Dimensional DW
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
                 ▼                ▼                ▼
              Weather          Rig Count        Energy
                 │
                 ▼
         Operational Risk
                 │
                 ▼
        Analytical SQL Views
                 │
         ┌───────┴─────────┐
         ▼                 ▼
   Data Quality       Observability
         │                 │
         └────────┬────────┘
                  ▼
          Streamlit Dashboard