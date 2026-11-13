-- ORIOM7 LAB Inventory & Procurement foundation.
-- Apply after 013_equipment_manager.sql. All records are scoped to trusted auth subjects.

CREATE TABLE IF NOT EXISTS lab_inventory_suppliers (
  supplier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  name TEXT NOT NULL CHECK (char_length(name) BETWEEN 2 AND 180),
  contact_name TEXT,
  email TEXT,
  phone TEXT,
  website TEXT,
  address TEXT,
  compliance_reference TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (supplier_id, owner_subject)
);
CREATE UNIQUE INDEX IF NOT EXISTS lab_inventory_supplier_name_unique
  ON lab_inventory_suppliers(owner_subject, lower(name));

CREATE TABLE IF NOT EXISTS lab_inventory_items (
  item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  sku TEXT NOT NULL CHECK (char_length(sku) BETWEEN 2 AND 100),
  name TEXT NOT NULL CHECK (char_length(name) BETWEEN 2 AND 180),
  category TEXT NOT NULL CHECK (char_length(category) BETWEEN 2 AND 100),
  description TEXT,
  unit TEXT NOT NULL CHECK (char_length(unit) BETWEEN 1 AND 30),
  reorder_level NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
  quantity_on_hand NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
  average_unit_cost NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (average_unit_cost >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  preferred_supplier_id UUID,
  hazard_classification TEXT,
  safety_data_sheet_reference TEXT,
  storage_requirements TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','quarantined')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (item_id, owner_subject),
  UNIQUE (owner_subject, sku),
  FOREIGN KEY (preferred_supplier_id, owner_subject)
    REFERENCES lab_inventory_suppliers(supplier_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_inventory_items_owner_name_idx
  ON lab_inventory_items(owner_subject, category, name);

CREATE TABLE IF NOT EXISTS lab_inventory_lots (
  lot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID NOT NULL,
  owner_subject TEXT NOT NULL,
  lot_code TEXT NOT NULL,
  supplier_id UUID,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expiry_date DATE,
  quantity_received NUMERIC(18,4) NOT NULL CHECK (quantity_received > 0),
  quantity_remaining NUMERIC(18,4) NOT NULL CHECK (quantity_remaining >= 0),
  unit_cost NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  inspection_status TEXT NOT NULL DEFAULT 'pending' CHECK (inspection_status IN ('pending','accepted','rejected','quarantined')),
  certificate_reference TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (lot_id, owner_subject),
  UNIQUE (item_id, owner_subject, lot_code),
  FOREIGN KEY (item_id, owner_subject) REFERENCES lab_inventory_items(item_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY (supplier_id, owner_subject) REFERENCES lab_inventory_suppliers(supplier_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_inventory_lots_expiry_idx
  ON lab_inventory_lots(owner_subject, expiry_date) WHERE quantity_remaining > 0;

CREATE TABLE IF NOT EXISTS lab_inventory_movements (
  movement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID NOT NULL,
  lot_id UUID,
  owner_subject TEXT NOT NULL,
  movement_type TEXT NOT NULL CHECK (movement_type IN ('receipt','issue','adjustment','write_off')),
  quantity_delta NUMERIC(18,4) NOT NULL CHECK (quantity_delta <> 0),
  unit_cost NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
  reference TEXT,
  reason TEXT NOT NULL CHECK (char_length(reason) BETWEEN 3 AND 1000),
  recorded_by TEXT NOT NULL CHECK (char_length(recorded_by) BETWEEN 2 AND 160),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (item_id, owner_subject) REFERENCES lab_inventory_items(item_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY (lot_id, owner_subject) REFERENCES lab_inventory_lots(lot_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_inventory_movements_timeline_idx
  ON lab_inventory_movements(item_id, created_at DESC);

CREATE TABLE IF NOT EXISTS lab_inventory_requisitions (
  requisition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  requested_by TEXT NOT NULL,
  purpose TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted','approved','rejected','ordered','cancelled')),
  lines JSONB NOT NULL CHECK (jsonb_typeof(lines)='array' AND jsonb_array_length(lines)>0),
  needed_by DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS lab_inventory_requisitions_owner_idx
  ON lab_inventory_requisitions(owner_subject, created_at DESC);

CREATE TABLE IF NOT EXISTS lab_inventory_purchase_orders (
  purchase_order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  supplier_id UUID NOT NULL,
  requisition_id UUID,
  order_number TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'issued' CHECK (status IN ('draft','issued','part_received','received','cancelled')),
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  expected_at DATE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(owner_subject, order_number),
  FOREIGN KEY (supplier_id, owner_subject) REFERENCES lab_inventory_suppliers(supplier_id, owner_subject) ON DELETE RESTRICT,
  FOREIGN KEY (requisition_id) REFERENCES lab_inventory_requisitions(requisition_id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS lab_inventory_purchase_order_lines (
  line_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  purchase_order_id UUID NOT NULL REFERENCES lab_inventory_purchase_orders(purchase_order_id) ON DELETE RESTRICT,
  item_id UUID NOT NULL,
  owner_subject TEXT NOT NULL,
  quantity_ordered NUMERIC(18,4) NOT NULL CHECK (quantity_ordered > 0),
  quantity_received NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (quantity_received >= 0 AND quantity_received <= quantity_ordered),
  unit_cost NUMERIC(18,4) NOT NULL CHECK (unit_cost >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (item_id, owner_subject) REFERENCES lab_inventory_items(item_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_inventory_po_lines_order_idx ON lab_inventory_purchase_order_lines(purchase_order_id);

-- Ledger entries are immutable; corrections must be compensating movements.
CREATE OR REPLACE FUNCTION prevent_lab_inventory_movement_mutation()
RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION 'inventory movements are append-only'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS lab_inventory_movements_no_mutation ON lab_inventory_movements;
CREATE TRIGGER lab_inventory_movements_no_mutation
  BEFORE UPDATE OR DELETE ON lab_inventory_movements
  FOR EACH ROW EXECUTE FUNCTION prevent_lab_inventory_movement_mutation();

COMMENT ON TABLE lab_inventory_items IS 'Owner-scoped laboratory stock register. Hazard data is descriptive; this system does not authorize chemical handling or purchasing.';
COMMENT ON TABLE lab_inventory_movements IS 'Append-only stock ledger; quantity_on_hand is a transactionally maintained balance.';
