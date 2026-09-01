-- Lender_Matching — Postgres server database schema (32.198.162.66)
--
-- Same exact table design as backend/db_schemas/supabase/schema.sql, on
-- purpose — see backend/db_schemas/README.md for why. This database will
-- hold the client's real lender data eventually: their exact attribute
-- names become new rows in `attributes` (and matching `eligibility_rules`
-- rows), not new columns or a different table shape. That way the backend
-- app code doesn't need to change no matter which of the two databases
-- DATABASE_URL points at.
--
-- Currently empty — no data loaded yet.

CREATE TABLE banks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    -- one of: 'excel_import', 'manual_calibration', 'admin_manual' — free
    -- text, not an enum, since the set of sources is expected to grow.
    source VARCHAR(40) NOT NULL DEFAULT 'excel_import'
);

CREATE TABLE home_loan_products (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER NOT NULL REFERENCES banks(id),
    product_name VARCHAR(120) NOT NULL
);

-- The catalog of possible criteria. Small, admin-managed, rarely changes.
CREATE TABLE attributes (
    id SERIAL PRIMARY KEY,
    key VARCHAR(80) NOT NULL UNIQUE,
    label VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL,
    -- one of: 'number', 'boolean', 'text'
    data_type VARCHAR(20) NOT NULL
);

-- One row = one fact about a product (an eligibility condition, or a
-- stored display/scoring value when operator='fact').
CREATE TABLE eligibility_rules (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES home_loan_products(id),
    attribute_id INTEGER NOT NULL REFERENCES attributes(id),
    -- one of: '>=', '<=', '==', 'required', 'in', 'fact', 'any_of', 'between'
    operator VARCHAR(10) NOT NULL,
    value VARCHAR(255) NOT NULL,
    CONSTRAINT uq_rule_scope UNIQUE (product_id, attribute_id)
);

-- A bank's relationship/priority signal with us. Keyed by bank_name, not a
-- foreign key, so it survives a full reload of the banks table.
CREATE TABLE bank_bias_facts (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(120) NOT NULL,
    metric_key VARCHAR(80) NOT NULL,
    value VARCHAR(255) NOT NULL,
    CONSTRAINT uq_bank_bias_metric UNIQUE (bank_name, metric_key)
);
