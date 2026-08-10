# Oil & Gas Data Engineering Project

## Objective

Develop a production-style ETL pipeline for the Oil & Gas industry using:

- Python
- PostgreSQL
- SQL
- REST APIs
- Data Warehouse
- Power BI
--# - Docker
--# - Airflow

## Pipeline

API → Extract → Transform → PostgreSQL → Data Warehouse → Analytics

# Oil & Gas Data Engineering Project

End-to-end Data Engineering project combining atmospheric forecasts, marine forecasts, energy prices, and global rig-count data into a PostgreSQL analytical warehouse.

The project simulates a real offshore energy decision-support platform using Python, SQL, APIs, Parquet, PostgreSQL, operational risk logic, and analytical views.

---

## Project Objectives

The pipeline integrates multiple data domains relevant to offshore oil and gas operations:

- Atmospheric weather forecasts
- Marine and wave forecasts
- Offshore operational weather risk
- Baker Hughes worldwide rig counts
- EIA energy prices
- Asset and location metadata

The final warehouse is designed to support Power BI dashboards and operational analytics.

---

## Architecture

```text
Open-Meteo Atmospheric API
Open-Meteo Marine API
EIA Energy API
Baker Hughes Rig Count Workbook
            |
            v
        Extraction
            |
            v
         Bronze
      JSON / Excel
            |
            v
      Transformation
            |
            v
         Silver
         Parquet
            |
            v
      PostgreSQL DW
            |
     +------+------+------+
     |             |      |
  Weather        Energy   Rig Count
     |
     v
Operational Risk Engine
     |
     v
Analytical SQL Views
     |
     v
Data Quality Validation
     |
     v
Power BI
