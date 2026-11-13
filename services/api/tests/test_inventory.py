import pytest
from pydantic import ValidationError


def test_inventory_item_rejects_invalid_sku_and_negative_reorder_level():
    from inventory import ItemCreate
    item = ItemCreate(sku="CHEM-001", name="Buffer solution", category="reagents", unit="litre", reorder_level="2.5000")
    assert item.currency == "USD"
    assert item.reorder_level > 0
    with pytest.raises(ValidationError):
        ItemCreate(sku=" ", name="Buffer solution", category="reagents", unit="litre")
    with pytest.raises(ValidationError):
        ItemCreate(sku="CHEM-002", name="Buffer solution", category="reagents", unit="litre", reorder_level="-1")


def test_inventory_requisition_requires_lines_and_positive_quantities():
    from inventory import RequisitionCreate
    import uuid
    req = RequisitionCreate(requested_by="Research team", purpose="Prepare materials for assay", lines=[{"item_id":str(uuid.uuid4()),"quantity":"2.5"}])
    assert len(req.lines) == 1
    with pytest.raises(ValidationError):
        RequisitionCreate(requested_by="Research team", purpose="Prepare materials", lines=[])
    with pytest.raises(ValidationError):
        RequisitionCreate(requested_by="Research team", purpose="Prepare materials", lines=[{"item_id":str(uuid.uuid4()),"quantity":"0"}])


def test_purchase_order_and_goods_receipt_validation():
    from inventory import PurchaseOrderCreate, GoodsReceiptCreate
    import uuid
    po = PurchaseOrderCreate(supplier_id=uuid.uuid4(), order_number="PO-2026-001", lines=[{"item_id":str(uuid.uuid4()),"quantity":"5","unit_cost":"2.25"}])
    assert po.currency == "USD"
    receipt = GoodsReceiptCreate(line_id=uuid.uuid4(), quantity="2", lot_code="LOT-001", recorded_by="Receiving technician")
    assert receipt.inspection_status == "pending"
    with pytest.raises(ValidationError):
        GoodsReceiptCreate(line_id=uuid.uuid4(), quantity="-1", lot_code="LOT-001", recorded_by="Technician")

def test_stock_issue_requires_lot_and_positive_quantity():
    from inventory import StockIssueCreate
    import uuid
    issue = StockIssueCreate(lot_id=uuid.uuid4(), quantity="0.25", reason="Research sample usage", recorded_by="Lab technician")
    assert issue.movement_type == "issue"
    with pytest.raises(ValidationError):
        StockIssueCreate(lot_id=uuid.uuid4(), quantity="0", reason="Research sample usage", recorded_by="Lab technician")


def test_inventory_currency_is_a_three_letter_code():
    from inventory import ItemCreate
    with pytest.raises(ValidationError):
        ItemCreate(sku="SKU-1", name="Sample vial", category="consumables", unit="each", currency="US")

def test_lot_inspection_only_accepts_defined_dispositions():
    from inventory import LotInspectionUpdate
    assert LotInspectionUpdate(inspection_status="accepted").inspection_status == "accepted"
    with pytest.raises(ValidationError):
        LotInspectionUpdate(inspection_status="released")
