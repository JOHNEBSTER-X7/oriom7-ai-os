"""ORIOM7 LAB inventory, suppliers, requisitions and procurement APIs.

This module tracks stock and records only. It does not authorize procurement,
hazardous-material handling, storage, disposal or regulatory compliance.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from accessibility import authenticated_subject

router = APIRouter(prefix="/v1/labs/inventory", tags=["laboratory-inventory"])


def _text(value: str) -> str:
    return " ".join(value.split())


async def _pool(request: Request):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(503, detail={"code": "lab_inventory_database_unavailable"})
    return pool


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=4000)
    unit: str = Field(min_length=1, max_length=30)
    reorder_level: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=4)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    preferred_supplier_id: uuid.UUID | None = None
    hazard_classification: str | None = Field(default=None, max_length=160)
    safety_data_sheet_reference: str | None = Field(default=None, max_length=1000)
    storage_requirements: str | None = Field(default=None, max_length=2000)

    @field_validator("sku", "name", "category", "unit", "currency")
    @classmethod
    def normalise(cls, value: str) -> str:
        value = _text(value).upper() if len(value) == 3 else _text(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=180)
    contact_name: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=60)
    website: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=2000)
    compliance_reference: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = _text(value)
        if len(value) < 2:
            raise ValueError("name must contain at least two non-space characters")
        return value


class RequisitionLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)


class RequisitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requested_by: str = Field(min_length=2, max_length=160)
    purpose: str = Field(min_length=3, max_length=1000)
    needed_by: date | None = None
    lines: list[RequisitionLine] = Field(min_length=1, max_length=100)

    @field_validator("requested_by", "purpose")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = _text(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value


class PurchaseOrderLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    unit_cost: Decimal = Field(ge=0, max_digits=18, decimal_places=4)


class PurchaseOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: uuid.UUID
    requisition_id: uuid.UUID | None = None
    order_number: str = Field(min_length=2, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    expected_at: date | None = None
    notes: str | None = Field(default=None, max_length=4000)
    lines: list[PurchaseOrderLine] = Field(min_length=1, max_length=100)

    @field_validator("order_number")
    @classmethod
    def clean_order_number(cls, value: str) -> str:
        value = _text(value)
        if len(value) < 2:
            raise ValueError("order_number cannot be blank")
        return value

    @field_validator("currency")
    @classmethod
    def clean_currency(cls, value: str) -> str:
        return _text(value).upper()


class GoodsReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    lot_code: str = Field(min_length=1, max_length=120)
    expiry_date: date | None = None
    unit_cost: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    inspection_status: Literal["pending", "accepted", "rejected", "quarantined"] = "pending"
    certificate_reference: str | None = Field(default=None, max_length=1000)
    recorded_by: str = Field(min_length=2, max_length=160)
    reason: str = Field(default="Goods received against purchase order", min_length=3, max_length=1000)


def _item(row: Any) -> dict[str, Any]:
    return {k: (str(row[k]) if isinstance(row[k], Decimal) else row[k]) for k in (
        "item_id","sku","name","category","description","unit","reorder_level",
        "quantity_on_hand","average_unit_cost","currency","preferred_supplier_id",
        "hazard_classification","safety_data_sheet_reference","storage_requirements","status"
    )}


def _supplier(row: Any) -> dict[str, Any]:
    return {k: row[k] for k in ("supplier_id","name","contact_name","email","phone","website","address","compliance_reference","notes","created_at")}


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        if payload.preferred_supplier_id:
            found = await con.fetchval("SELECT 1 FROM lab_inventory_suppliers WHERE supplier_id=$1 AND owner_subject=$2", payload.preferred_supplier_id, subject)
            if not found:
                raise HTTPException(404, detail={"code": "inventory_supplier_not_found"})
        try:
            row = await con.fetchrow(
                """INSERT INTO lab_inventory_items(owner_subject,sku,name,category,description,unit,reorder_level,currency,preferred_supplier_id,hazard_classification,safety_data_sheet_reference,storage_requirements)
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                   RETURNING item_id::text,sku,name,category,description,unit,reorder_level,quantity_on_hand,average_unit_cost,currency,preferred_supplier_id::text,hazard_classification,safety_data_sheet_reference,storage_requirements,status""",
                subject,payload.sku,payload.name,payload.category,payload.description,payload.unit,payload.reorder_level,payload.currency,payload.preferred_supplier_id,payload.hazard_classification,payload.safety_data_sheet_reference,payload.storage_requirements)
        except Exception as exc:
            if "lab_inventory_items_owner_sku_key" in str(exc):
                raise HTTPException(409, detail={"code": "inventory_sku_exists"}) from exc
            raise
    return _item(row)


@router.get("/items")
async def list_items(request: Request, low_stock: bool = False, limit: int = Query(100,ge=1,le=200), offset: int = Query(0,ge=0,le=100000), subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        rows = await con.fetch(
            """SELECT item_id::text,sku,name,category,description,unit,reorder_level,quantity_on_hand,average_unit_cost,currency,preferred_supplier_id::text,hazard_classification,safety_data_sheet_reference,storage_requirements,status
               FROM lab_inventory_items WHERE owner_subject=$1 AND ($2=false OR quantity_on_hand<=reorder_level)
               ORDER BY category,name LIMIT $3 OFFSET $4""",subject,low_stock,limit,offset)
        total = await con.fetchval("SELECT count(*) FROM lab_inventory_items WHERE owner_subject=$1 AND ($2=false OR quantity_on_hand<=reorder_level)",subject,low_stock)
    return {"items":[_item(r) for r in rows],"total":total,"limit":limit,"offset":offset}


@router.post("/suppliers", status_code=status.HTTP_201_CREATED)
async def create_supplier(payload: SupplierCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        row=await con.fetchrow(
            """INSERT INTO lab_inventory_suppliers(owner_subject,name,contact_name,email,phone,website,address,compliance_reference,notes)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
               RETURNING supplier_id::text,name,contact_name,email,phone,website,address,compliance_reference,notes,created_at""",
            subject,payload.name,payload.contact_name,payload.email,payload.phone,payload.website,payload.address,payload.compliance_reference,payload.notes)
    return _supplier(row)


@router.get("/suppliers")
async def list_suppliers(request: Request, limit: int = Query(100,ge=1,le=200), subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch("""SELECT supplier_id::text,name,contact_name,email,phone,website,address,compliance_reference,notes,created_at
                               FROM lab_inventory_suppliers WHERE owner_subject=$1 ORDER BY name LIMIT $2""",subject,limit)
    return {"items":[_supplier(r) for r in rows],"total":len(rows)}


@router.post("/requisitions", status_code=status.HTTP_201_CREATED)
async def create_requisition(payload: RequisitionCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            for line in payload.lines:
                if not await con.fetchval("SELECT 1 FROM lab_inventory_items WHERE item_id=$1 AND owner_subject=$2 AND status='active'",line.item_id,subject):
                    raise HTTPException(404,detail={"code":"inventory_item_not_found"})
            row=await con.fetchrow(
                """INSERT INTO lab_inventory_requisitions(owner_subject,requested_by,purpose,needed_by,lines)
                   VALUES($1,$2,$3,$4,$5::jsonb) RETURNING requisition_id::text,requested_by,purpose,status,needed_by,lines,created_at""",
                subject,payload.requested_by,payload.purpose,payload.needed_by,
                __import__("json").dumps([{"item_id":str(x.item_id),"quantity":str(x.quantity)} for x in payload.lines]))
    return dict(row)


@router.get("/requisitions")
async def list_requisitions(request: Request, limit: int = Query(100,ge=1,le=200), subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch("SELECT requisition_id::text,requested_by,purpose,status,needed_by,lines,created_at,updated_at FROM lab_inventory_requisitions WHERE owner_subject=$1 ORDER BY created_at DESC LIMIT $2",subject,limit)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
async def create_purchase_order(payload: PurchaseOrderCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            if not await con.fetchval("SELECT 1 FROM lab_inventory_suppliers WHERE supplier_id=$1 AND owner_subject=$2",payload.supplier_id,subject):
                raise HTTPException(404,detail={"code":"inventory_supplier_not_found"})
            if payload.requisition_id and not await con.fetchval("SELECT 1 FROM lab_inventory_requisitions WHERE requisition_id=$1 AND owner_subject=$2 AND status IN ('approved','submitted')",payload.requisition_id,subject):
                raise HTTPException(404,detail={"code":"inventory_requisition_not_found_or_not_eligible"})
            for line in payload.lines:
                if not await con.fetchval("SELECT 1 FROM lab_inventory_items WHERE item_id=$1 AND owner_subject=$2 AND status='active'",line.item_id,subject):
                    raise HTTPException(404,detail={"code":"inventory_item_not_found"})
            po=await con.fetchrow(
                """INSERT INTO lab_inventory_purchase_orders(owner_subject,supplier_id,requisition_id,order_number,currency,expected_at,notes)
                   VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING purchase_order_id::text,order_number,status,currency,expected_at,created_at""",
                subject,payload.supplier_id,payload.requisition_id,payload.order_number,payload.currency,payload.expected_at,payload.notes)
            for line in payload.lines:
                await con.execute("""INSERT INTO lab_inventory_purchase_order_lines(purchase_order_id,item_id,owner_subject,quantity_ordered,unit_cost)
                                     VALUES($1,$2,$3,$4,$5)""",uuid.UUID(po["purchase_order_id"]),line.item_id,subject,line.quantity,line.unit_cost)
            if payload.requisition_id:
                await con.execute("UPDATE lab_inventory_requisitions SET status='ordered',updated_at=now() WHERE requisition_id=$1 AND owner_subject=$2",payload.requisition_id,subject)
    return dict(po)


@router.get("/purchase-orders")
async def list_purchase_orders(request: Request, limit: int = Query(100,ge=1,le=200), subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch("""SELECT p.purchase_order_id::text,p.order_number,p.status,p.currency,p.expected_at,s.name AS supplier_name,p.created_at,
                                     COALESCE(jsonb_agg(jsonb_build_object('line_id',l.line_id::text,'item_id',l.item_id::text,'quantity_ordered',l.quantity_ordered::text,'quantity_received',l.quantity_received::text,'unit_cost',l.unit_cost::text)) FILTER (WHERE l.line_id IS NOT NULL),'[]'::jsonb) AS lines
                               FROM lab_inventory_purchase_orders p JOIN lab_inventory_suppliers s ON s.supplier_id=p.supplier_id AND s.owner_subject=p.owner_subject
                               LEFT JOIN lab_inventory_purchase_order_lines l ON l.purchase_order_id=p.purchase_order_id
                               WHERE p.owner_subject=$1 GROUP BY p.purchase_order_id,s.name ORDER BY p.created_at DESC LIMIT $2""",subject,limit)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.post("/receipts", status_code=status.HTTP_201_CREATED)
async def receive_goods(payload: GoodsReceiptCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            line=await con.fetchrow(
                """SELECT l.line_id,l.item_id,l.quantity_ordered,l.quantity_received,l.unit_cost,p.purchase_order_id,p.supplier_id,p.status,p.currency
                   FROM lab_inventory_purchase_order_lines l JOIN lab_inventory_purchase_orders p ON p.purchase_order_id=l.purchase_order_id
                   WHERE l.line_id=$1 AND l.owner_subject=$2 AND p.owner_subject=$2 FOR UPDATE OF l,p""",payload.line_id,subject)
            if line is None or line["status"] not in ("issued","part_received"):
                raise HTTPException(404,detail={"code":"inventory_purchase_order_line_not_found_or_closed"})
            if line["quantity_received"] + payload.quantity > line["quantity_ordered"]:
                raise HTTPException(409,detail={"code":"inventory_receipt_exceeds_ordered_quantity"})
            item=await con.fetchrow("SELECT item_id,quantity_on_hand,average_unit_cost FROM lab_inventory_items WHERE item_id=$1 AND owner_subject=$2 FOR UPDATE",line["item_id"],subject)
            if item is None:
                raise HTTPException(404,detail={"code":"inventory_item_not_found"})
            lot=await con.fetchrow(
                """INSERT INTO lab_inventory_lots(item_id,owner_subject,lot_code,supplier_id,expiry_date,quantity_received,quantity_remaining,unit_cost,currency,inspection_status,certificate_reference)
                   VALUES($1,$2,$3,$4,$5,$6,$6,$7,$8,$9,$10)
                   RETURNING lot_id::text""",
                line["item_id"],subject,payload.lot_code,line["supplier_id"],payload.expiry_date,payload.quantity,payload.unit_cost,payload.certificate_reference and line["currency"] or line["currency"],payload.inspection_status,payload.certificate_reference)
            await con.execute(
                """INSERT INTO lab_inventory_movements(item_id,lot_id,owner_subject,movement_type,quantity_delta,unit_cost,reference,reason,recorded_by)
                   VALUES($1,$2,$3,'receipt',$4,$5,$6,$7,$8)""",
                line["item_id"],uuid.UUID(lot["lot_id"]),subject,payload.quantity,payload.unit_cost,str(line["purchase_order_id"]),payload.reason,payload.recorded_by)
            new_qty=item["quantity_on_hand"]+payload.quantity
            old_value=item["quantity_on_hand"]*item["average_unit_cost"]
            new_cost=(old_value+payload.quantity*payload.unit_cost)/new_qty if new_qty else Decimal("0")
            await con.execute("UPDATE lab_inventory_items SET quantity_on_hand=$2,average_unit_cost=$3,updated_at=now() WHERE item_id=$1 AND owner_subject=$4",line["item_id"],new_qty,new_cost,subject)
            await con.execute("UPDATE lab_inventory_purchase_order_lines SET quantity_received=quantity_received+$2 WHERE line_id=$1",payload.line_id,payload.quantity)
            remaining=await con.fetchval("SELECT bool_and(quantity_received>=quantity_ordered) FROM lab_inventory_purchase_order_lines WHERE purchase_order_id=$1",line["purchase_order_id"])
            any_received=await con.fetchval("SELECT bool_or(quantity_received>0) FROM lab_inventory_purchase_order_lines WHERE purchase_order_id=$1",line["purchase_order_id"])
            new_status="received" if remaining else ("part_received" if any_received else "issued")
            await con.execute("UPDATE lab_inventory_purchase_orders SET status=$2,updated_at=now() WHERE purchase_order_id=$1",line["purchase_order_id"],new_status)
    return {"lot_id":lot["lot_id"],"item_id":str(line["item_id"]),"quantity_received":str(payload.quantity),"inspection_status":payload.inspection_status,"purchase_order_status":new_status}


@router.get("/summary")
async def inventory_summary(request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        row=await con.fetchrow(
            """SELECT count(*)::int AS total_items,
                 count(*) FILTER(WHERE quantity_on_hand<=reorder_level)::int AS low_stock_items,
                 COALESCE(sum(quantity_on_hand*average_unit_cost),0)::numeric(18,2)::text AS inventory_value,
                 (SELECT count(*)::int FROM lab_inventory_lots WHERE owner_subject=$1 AND quantity_remaining>0 AND expiry_date<CURRENT_DATE) AS expired_lots,
                 (SELECT count(*)::int FROM lab_inventory_lots WHERE owner_subject=$1 AND quantity_remaining>0 AND expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE+30) AS expiring_30_days,
                 (SELECT count(*)::int FROM lab_inventory_purchase_orders WHERE owner_subject=$1 AND status IN ('issued','part_received')) AS open_purchase_orders
               FROM lab_inventory_items WHERE owner_subject=$1""",subject)
    return dict(row)
