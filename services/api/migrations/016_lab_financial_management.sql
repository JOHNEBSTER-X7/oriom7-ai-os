-- ORIOM7 LAB Financial Management & Project Costing.
-- Apply after 015_lab_quality_compliance.sql. Operational management records, not statutory accounts.

CREATE TABLE IF NOT EXISTS lab_cost_centres (
  cost_centre_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  code TEXT NOT NULL CHECK (char_length(code) BETWEEN 2 AND 40),
  name TEXT NOT NULL CHECK (char_length(name) BETWEEN 2 AND 160),
  description TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(owner_subject, code), UNIQUE(cost_centre_id, owner_subject)
);

CREATE TABLE IF NOT EXISTS lab_budgets (
  budget_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  project_id UUID,
  cost_centre_id UUID,
  name TEXT NOT NULL CHECK (char_length(name) BETWEEN 3 AND 160),
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  approved_amount NUMERIC(20,4) NOT NULL CHECK (approved_amount >= 0),
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved','closed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(budget_id, owner_subject),
  FOREIGN KEY(project_id, owner_subject) REFERENCES lab_projects(project_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY(cost_centre_id, owner_subject) REFERENCES lab_cost_centres(cost_centre_id, owner_subject) ON DELETE RESTRICT,
  CHECK(period_end >= period_start)
);
CREATE INDEX IF NOT EXISTS lab_budgets_owner_period_idx ON lab_budgets(owner_subject, period_start, period_end);

CREATE TABLE IF NOT EXISTS lab_funding_grants (
  grant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  project_id UUID,
  funder_name TEXT NOT NULL CHECK (char_length(funder_name) BETWEEN 2 AND 180),
  grant_reference TEXT,
  currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  awarded_amount NUMERIC(20,4) NOT NULL CHECK (awarded_amount >= 0),
  start_date DATE,
  end_date DATE,
  restrictions TEXT,
  status TEXT NOT NULL DEFAULT 'prospective' CHECK (status IN ('prospective','awarded','active','completed','withdrawn')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(grant_id, owner_subject),
  FOREIGN KEY(project_id, owner_subject) REFERENCES lab_projects(project_id, owner_subject) ON DELETE RESTRICT,
  CHECK(end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
CREATE UNIQUE INDEX IF NOT EXISTS lab_grant_reference_unique
  ON lab_funding_grants(owner_subject, grant_reference) WHERE grant_reference IS NOT NULL;

CREATE TABLE IF NOT EXISTS lab_financial_transactions (
  transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  project_id UUID,
  experiment_id UUID,
  budget_id UUID,
  grant_id UUID,
  cost_centre_id UUID,
  equipment_id UUID,
  inventory_item_id UUID,
  transaction_type TEXT NOT NULL CHECK(transaction_type IN ('expense','credit','adjustment')),
  category TEXT NOT NULL CHECK(char_length(category) BETWEEN 2 AND 80),
  description TEXT NOT NULL CHECK(char_length(description) BETWEEN 3 AND 500),
  amount NUMERIC(20,4) NOT NULL CHECK(amount > 0),
  currency CHAR(3) NOT NULL CHECK(currency ~ '^[A-Z]{3}$'),
  transaction_date DATE NOT NULL,
  supplier_name TEXT,
  invoice_reference TEXT,
  recorded_by TEXT NOT NULL CHECK(char_length(recorded_by) BETWEEN 2 AND 160),
  source_reference TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(project_id, owner_subject) REFERENCES lab_projects(project_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY(experiment_id, owner_subject) REFERENCES lab_experiments(experiment_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY(budget_id, owner_subject) REFERENCES lab_budgets(budget_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY(grant_id, owner_subject) REFERENCES lab_funding_grants(grant_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY(cost_centre_id, owner_subject) REFERENCES lab_cost_centres(cost_centre_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY(equipment_id, owner_subject) REFERENCES lab_equipment(equipment_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY(inventory_item_id, owner_subject) REFERENCES lab_inventory_items(item_id, owner_subject) ON DELETE RESTRICT,
  CHECK(experiment_id IS NULL OR project_id IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS lab_financial_invoice_unique
  ON lab_financial_transactions(owner_subject, supplier_name, invoice_reference)
  WHERE invoice_reference IS NOT NULL AND supplier_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS lab_financial_tx_owner_date_idx
  ON lab_financial_transactions(owner_subject, transaction_date DESC);

CREATE TABLE IF NOT EXISTS lab_asset_depreciation (
  depreciation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  equipment_id UUID NOT NULL,
  acquisition_date DATE NOT NULL,
  acquisition_cost NUMERIC(20,4) NOT NULL CHECK(acquisition_cost > 0),
  currency CHAR(3) NOT NULL CHECK(currency ~ '^[A-Z]{3}$'),
  useful_life_months INTEGER NOT NULL CHECK(useful_life_months BETWEEN 1 AND 1200),
  residual_value NUMERIC(20,4) NOT NULL DEFAULT 0 CHECK(residual_value >= 0),
  method TEXT NOT NULL DEFAULT 'straight_line' CHECK(method = 'straight_line'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(owner_subject, equipment_id),
  FOREIGN KEY(equipment_id, owner_subject) REFERENCES lab_equipment(equipment_id, owner_subject) ON DELETE RESTRICT,
  CHECK(residual_value <= acquisition_cost)
);

CREATE OR REPLACE FUNCTION prevent_lab_financial_transaction_mutation()
RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION 'financial transaction ledger is append-only; post a correcting entry'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS lab_financial_transactions_no_mutation ON lab_financial_transactions;
CREATE TRIGGER lab_financial_transactions_no_mutation
  BEFORE UPDATE OR DELETE ON lab_financial_transactions
  FOR EACH ROW EXECUTE FUNCTION prevent_lab_financial_transaction_mutation();

COMMENT ON TABLE lab_financial_transactions IS 'Append-only operational expense/credit ledger; not a general ledger or audited accounting record.';
COMMENT ON TABLE lab_asset_depreciation IS 'Straight-line planning schedule; not a tax depreciation determination or fixed-asset accounting subledger.';
