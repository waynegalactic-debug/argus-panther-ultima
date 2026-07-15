-- IP FORCE Database Schema
-- Neon PostgreSQL | Project: floral-term-24584346

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    rank INT,
    name VARCHAR(255),
    industry VARCHAR(255),
    revenue_usd BIGINT,
    market_cap_usd BIGINT,
    ticker VARCHAR(20),
    sector VARCHAR(100),
    price DECIMAL(10,2),
    pe_ratio DECIMAL(8,2),
    dividend_yield DECIMAL(5,2),
    beta DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    data_source VARCHAR(50),
    metric_name VARCHAR(100),
    metric_value DECIMAL(18,4),
    as_of_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crypto_market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    name VARCHAR(100),
    price_usd DECIMAL(18,8),
    market_cap_usd BIGINT,
    volume_24h_usd BIGINT,
    percent_change_24h DECIMAL(8,4),
    percent_change_7d DECIMAL(8,4),
    circulating_supply BIGINT,
    dominance_pct DECIMAL(6,2),
    as_of TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS macro_indicators (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10),
    indicator_name VARCHAR(100),
    indicator_value DECIMAL(18,4),
    year INT,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patent_landscape (
    id SERIAL PRIMARY KEY,
    title TEXT,
    authors TEXT,
    year INT,
    abstract TEXT,
    citation_count INT,
    link TEXT,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS time_series (
    id SERIAL PRIMARY KEY,
    series_type VARCHAR(50),
    entity VARCHAR(50),
    date DATE,
    value DECIMAL(18,4),
    metric_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_mcap ON companies(market_cap_usd DESC);
CREATE INDEX idx_crypto_symbol ON crypto_market_data(symbol);
CREATE INDEX idx_macro_country_year ON macro_indicators(country_code, year);
CREATE INDEX idx_macro_indicator ON macro_indicators(indicator_name);
CREATE INDEX idx_patent_category ON patent_landscape(category);
CREATE INDEX idx_timeseries_entity_date ON time_series(entity, date);
