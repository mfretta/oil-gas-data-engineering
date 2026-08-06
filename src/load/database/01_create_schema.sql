CREATE TABLE IF NOT EXISTS dim_location (

    location_key SERIAL PRIMARY KEY,

    location_id VARCHAR(50) UNIQUE,

    location_name VARCHAR(100),

    country VARCHAR(100),

    latitude DECIMAL(8,5),

    longitude DECIMAL(8,5)

);


CREATE TABLE IF NOT EXISTS dim_time (

    time_key SERIAL PRIMARY KEY,

    timestamp TIMESTAMP UNIQUE,

    date DATE,

    hour INTEGER,

    month INTEGER,

    season VARCHAR(20)

);


CREATE TABLE IF NOT EXISTS dim_asset (

    asset_key SERIAL PRIMARY KEY,

    asset_id VARCHAR(50) UNIQUE,

    asset_name VARCHAR(100),

    asset_type VARCHAR(50)

);


CREATE TABLE IF NOT EXISTS fact_weather (

    weather_key SERIAL PRIMARY KEY,

    time_key INTEGER REFERENCES dim_time(time_key),

    location_key INTEGER REFERENCES dim_location(location_key),

    asset_key INTEGER REFERENCES dim_asset(asset_key),

    temperature_c DECIMAL(5,2),

    humidity INTEGER,

    wind_kmh DECIMAL(5,2),

    ingestion_time TIMESTAMP

);