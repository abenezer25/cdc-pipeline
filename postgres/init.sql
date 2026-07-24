CREATE SCHEMA IF NOT EXISTS sentinel;

-- Accounts Table
CREATE TABLE IF NOT EXISTS sentinel.accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(30) NOT NULL DEFAULT 'SAVINGS',
    balance NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    risk_score INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Transactions Table
CREATE TABLE IF NOT EXISTS sentinel.transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    source_account_id VARCHAR(50) NOT NULL,
    destination_account_id VARCHAR(50) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    transaction_type VARCHAR(30) NOT NULL DEFAULT 'TRANSFER',
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Replica Identities for Full Debezium CDC
ALTER TABLE sentinel.accounts REPLICA IDENTITY FULL;
ALTER TABLE sentinel.transactions REPLICA IDENTITY FULL;

-- Seed Data
INSERT INTO sentinel.accounts (account_id, owner_name, account_type, balance, status, risk_score) VALUES
('ACC-1001', 'Alice Smith', 'CHECKING', 12500.50, 'ACTIVE', 5),
('ACC-1002', 'Bob Jones', 'SAVINGS', 45000.00, 'ACTIVE', 2),
('ACC-1003', 'Charlie Brown', 'CORPORATE', 1200000.00, 'ACTIVE', 12),
('ACC-1004', 'Evan Wright', 'CHECKING', 890.20, 'FLAGGED', 75)
ON CONFLICT (account_id) DO NOTHING;

INSERT INTO sentinel.transactions (transaction_id, source_account_id, destination_account_id, amount, transaction_type, status) VALUES
('TX-9001', 'ACC-1001', 'ACC-1002', 250.00, 'TRANSFER', 'COMPLETED'),
('TX-9002', 'ACC-1003', 'ACC-1004', 15000.00, 'WIRE', 'COMPLETED')
ON CONFLICT (transaction_id) DO NOTHING;
