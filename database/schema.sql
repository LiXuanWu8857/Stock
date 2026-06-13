-- Stock Portfolio Management System - PostgreSQL Schema

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default user for single-user MVP
INSERT INTO users (id, email, name) VALUES (1, 'user@example.com', 'Portfolio Owner')
ON CONFLICT (id) DO NOTHING;

-- Holdings table
CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(5) NOT NULL CHECK (market IN ('TW', 'US')),
    shares NUMERIC(15, 4) NOT NULL DEFAULT 0,
    avg_cost NUMERIC(15, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, symbol, market)
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(5) NOT NULL CHECK (market IN ('TW', 'US')),
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    price NUMERIC(15, 4) NOT NULL,
    shares NUMERIC(15, 4) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily portfolio snapshots (for net profit / performance curves)
CREATE TABLE IF NOT EXISTS daily_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    invested_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    withdrawn_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    market_value NUMERIC(18, 4) NOT NULL DEFAULT 0,
    cash NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_asset NUMERIC(18, 4) NOT NULL DEFAULT 0,
    net_profit NUMERIC(18, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Dividends table
CREATE TABLE IF NOT EXISTS dividends (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(5) NOT NULL CHECK (market IN ('TW', 'US')),
    amount_per_share NUMERIC(15, 6) NOT NULL,
    shares_at_time NUMERIC(15, 4) NOT NULL,
    total_amount NUMERIC(15, 4) NOT NULL,
    ex_date DATE NOT NULL,
    pay_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol);
CREATE INDEX IF NOT EXISTS idx_holdings_market ON holdings(market);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions(symbol);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_market ON transactions(market);

CREATE INDEX IF NOT EXISTS idx_snapshots_user_id ON daily_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON daily_snapshots(date);

CREATE INDEX IF NOT EXISTS idx_dividends_user_id ON dividends(user_id);
CREATE INDEX IF NOT EXISTS idx_dividends_symbol ON dividends(symbol);
CREATE INDEX IF NOT EXISTS idx_dividends_ex_date ON dividends(ex_date);

-- Trigger function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for holdings updated_at
DROP TRIGGER IF EXISTS update_holdings_updated_at ON holdings;
CREATE TRIGGER update_holdings_updated_at
    BEFORE UPDATE ON holdings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
