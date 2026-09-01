-- Birbal Club — Supabase database schema
-- Mirrors backend/app/database.py exactly. That file is the source of
-- truth (SQLAlchemy creates these tables automatically); this .sql file is
-- a plain-SQL copy for reference / for running by hand with psql if needed.
--
-- Design: banks -> home_loan_products -> eligibility_rules, with
-- eligibility_rules pointing at a shared `attributes` catalog instead of
-- having one dedicated column per criterion. Adding a new criterion is a
-- data change (one attributes row + eligibility_rules rows), not a schema
-- migration.

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
-- Examples: key='min_cibil_score' category='Credit' data_type='number';
-- key='document_bank_statement' category='Documents' data_type='boolean'.
CREATE TABLE attributes (
    id SERIAL PRIMARY KEY,
    key VARCHAR(80) NOT NULL UNIQUE,
    label VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL,
    -- one of: 'number', 'boolean', 'text'
    data_type VARCHAR(20) NOT NULL
);

-- One row = one fact about a product. Most rows are eligibility conditions
-- ("this product needs this attribute to satisfy this operator against
-- this value"); rows with operator='fact' are just a stored value
-- (interest rate, tenure, ...) for display/scoring, not a condition.
CREATE TABLE eligibility_rules (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES home_loan_products(id),
    attribute_id INTEGER NOT NULL REFERENCES attributes(id),
    -- one of: '>=', '<=', '==', 'required', 'in', 'fact', 'any_of', 'between'
    operator VARCHAR(10) NOT NULL,
    -- always stored as text; parsed according to the attribute's data_type
    value VARCHAR(255) NOT NULL,
    CONSTRAINT uq_rule_scope UNIQUE (product_id, attribute_id)
);

-- A bank's relationship/priority signal with us (e.g. how many borrowers
-- we've recently placed with them) — separate from anything a lender data
-- file provides. Deliberately keyed by bank_name (not a foreign key to
-- banks.id) so it survives a full reload of the banks table untouched.
CREATE TABLE bank_bias_facts (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(120) NOT NULL,
    metric_key VARCHAR(80) NOT NULL,
    value VARCHAR(255) NOT NULL,
    CONSTRAINT uq_bank_bias_metric UNIQUE (bank_name, metric_key)
);
