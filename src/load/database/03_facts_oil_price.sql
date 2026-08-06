CREATE TABLE IF NOT EXISTS fact_oil_price
(
    oil_price_key SERIAL PRIMARY KEY,

    time_key INTEGER NOT NULL
        REFERENCES dim_time(time_key),

    product VARCHAR(30),

    price_usd NUMERIC(10,2),

    unit VARCHAR(20),

    source VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);