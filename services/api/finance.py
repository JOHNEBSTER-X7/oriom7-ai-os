"""ORIOM7 LAB project budgets, funding and operational cost records.

This is a project-costing aid, not statutory accounting, tax advice, grant assurance,
an audited ledger or a payment/procurement authorisation system.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from accessibility import authenticated_subject

router = APIRouter(prefix="/v1/labs/finance", tags=["laboratory-finance"])


def _clean(value: str) -> str:
    return " ".join(value.split())


def _currency(value: str) -> str:
    value = _clean(value).upper()
    if len(value) != 3 or not value.isalpha():
        raise ValueError("currency must be a three-letter ISO-style code")
    return value


async def _pool(request: Request):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(503, detail={"code": "lab_finance_database_unavailable"})
    return pool


class CostCentreCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("code", "name")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value


class BudgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: uuid.UUID | None = None
    cost_centre_id: uuid.UUID | None = None
    name: str = Field(min_length=3, max_length=160)
    period_start: date
    period_end: date
    currency: str = Field(min_length=3, max_length=3)
    approved_amount: Decimal = Field(ge=0, max_digits=20, decimal_places=4)
    status: Literal["draft", "approved"] = "draft"

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return _currency(value)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean(value)

    @field_validator("period_end")
    @classmethod
    def valid_period(cls, value: date, info):
        start = info.data.get("period_start")
        if start and value < start:
            raise ValueError("period_end cannot precede period_start")
        return value


class GrantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: uuid.UUID | None = None
    funder_name: str = Field(min_length=2, max_length=180)
    grant_reference: str | None = Field(default=None, max_length=120)
    currency: str = Field(min_length=3, max_length=3)
    awarded_amount: Decimal = Field(ge=0, max_digits=20, decimal_places=4)
    start_date: date | None = None
    end_date: date | None = None
    restrictions: str | None = Field(default=None, max_length=4000)
    status: Literal["prospective", "awarded", "active", "completed", "withdrawn"] = "prospective"

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return _currency(value)

    @field_validator("funder_name")
    @classmethod
    def clean_funder(cls, value: str) -> str:
        return _clean(value)

    @field_validator("end_date")
    @classmethod
    def valid_dates(cls, value: date | None, info):
        start = info.data.get("start_date")
        if value and start and value < start:
            raise ValueError("end_date cannot precede start_date")
        return value


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: uuid.UUID | None = None
    experiment_id: uuid.UUID | None = None
    budget_id: uuid.UUID | None = None
    grant_id: uuid.UUID | None = None
    cost_centre_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    inventory_item_id: uuid.UUID | None = None
    transaction_type: Literal["expense", "credit", "adjustment"] = "expense"
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=3, max_length=500)
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    currency: str = Field(min_length=3, max_length=3)
    transaction_date: date
    supplier_name: str | None = Field(default=None, max_length=180)
    invoice_reference: str | None = Field(default=None, max_length=120)
    recorded_by: str = Field(min_length=2, max_length=160)
    source_reference: str | None = Field(default=None, max_length=500)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return _currency(value)

    @field_validator("category", "description", "recorded_by")
    @classmethod
    def clean_required(cls, value: str) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value

    @field_validator("supplier_name", "invoice_reference", "source_reference")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        return _clean(value) if value else value

    @field_validator("experiment_id")
    @classmethod
    def experiment_requires_project(cls, value, info):
        if value and not info.data.get("project_id"):
            raise ValueError("experiment_id requires project_id")
        return value


class DepreciationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    equipment_id: uuid.UUID
    acquisition_date: date
    acquisition_cost: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    currency: str = Field(min_length=3, max_length=3)
    useful_life_months: int = Field(ge=1, le=1200)
    residual_value: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return _currency(value)

    @field_validator("residual_value")
    @classmethod
    def residual_within_cost(cls, value: Decimal, info):
        cost = info.data.get("acquisition_cost")
        if cost is not None and value > cost:
            raise ValueError("residual_value cannot exceed acquisition_cost")
        return value


@router.post("/cost-centres", status_code=status.HTTP_201_CREATED)
async def create_cost_centre(payload: CostCentreCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        try:
            row = await con.fetchrow(
                """INSERT INTO lab_cost_centres(owner_subject,code,name,description)
                   VALUES($1,$2,$3,$4) RETURNING cost_centre_id::text,code,name,description,active,created_at""",
                subject, payload.code, payload.name, payload.description)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, detail={"code": "cost_centre_code_exists"}) from exc
            raise
    return dict(row)


@router.get("/cost-centres")
async def list_cost_centres(request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        rows = await con.fetch("SELECT cost_centre_id::text,code,name,description,active,created_at FROM lab_cost_centres WHERE owner_subject=$1 ORDER BY code", subject)
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@router.post("/budgets", status_code=status.HTTP_201_CREATED)
async def create_budget(payload: BudgetCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """INSERT INTO lab_budgets(owner_subject,project_id,cost_centre_id,name,period_start,period_end,currency,approved_amount,status)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
               RETURNING budget_id::text,project_id::text,cost_centre_id::text,name,period_start,period_end,currency,approved_amount,status,created_at""",
            subject,payload.project_id,payload.cost_centre_id,payload.name,payload.period_start,payload.period_end,payload.currency,payload.approved_amount,payload.status)
    return dict(row)


@router.get("/budgets")
async def list_budgets(request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        rows = await con.fetch(
            """SELECT b.budget_id::text,b.project_id::text,b.cost_centre_id::text,b.name,b.period_start,b.period_end,b.currency,b.approved_amount,b.status,
                      COALESCE(SUM(CASE WHEN t.transaction_type='credit' THEN -t.amount WHEN t.transaction_type='expense' THEN t.amount ELSE t.amount END),0) AS net_spend
               FROM lab_budgets b LEFT JOIN lab_financial_transactions t ON t.budget_id=b.budget_id AND t.owner_subject=b.owner_subject
               WHERE b.owner_subject=$1 GROUP BY b.budget_id ORDER BY b.period_start DESC""", subject)
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@router.post("/grants", status_code=status.HTTP_201_CREATED)
async def create_grant(payload: GrantCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        try:
            row = await con.fetchrow(
                """INSERT INTO lab_funding_grants(owner_subject,project_id,funder_name,grant_reference,currency,awarded_amount,start_date,end_date,restrictions,status)
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                   RETURNING grant_id::text,project_id::text,funder_name,grant_reference,currency,awarded_amount,start_date,end_date,restrictions,status,created_at""",
                subject,payload.project_id,payload.funder_name,payload.grant_reference,payload.currency,payload.awarded_amount,payload.start_date,payload.end_date,payload.restrictions,payload.status)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, detail={"code": "grant_reference_exists"}) from exc
            raise
    return dict(row)


@router.get("/grants")
async def list_grants(request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        rows = await con.fetch(
            """SELECT g.grant_id::text,g.project_id::text,g.funder_name,g.grant_reference,g.currency,g.awarded_amount,g.start_date,g.end_date,g.status,
                      COALESCE(SUM(CASE WHEN t.transaction_type='credit' THEN -t.amount ELSE t.amount END),0) AS utilised_amount
               FROM lab_funding_grants g LEFT JOIN lab_financial_transactions t ON t.grant_id=g.grant_id AND t.owner_subject=g.owner_subject
               WHERE g.owner_subject=$1 GROUP BY g.grant_id ORDER BY g.created_at DESC""", subject)
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_transaction(payload: TransactionCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        try:
            row = await con.fetchrow(
                """INSERT INTO lab_financial_transactions(owner_subject,project_id,experiment_id,budget_id,grant_id,cost_centre_id,equipment_id,inventory_item_id,
                   transaction_type,category,description,amount,currency,transaction_date,supplier_name,invoice_reference,recorded_by,source_reference)
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
                   RETURNING transaction_id::text,project_id::text,experiment_id::text,budget_id::text,grant_id::text,transaction_type,category,description,amount,currency,transaction_date,supplier_name,invoice_reference,recorded_by,created_at""",
                subject,payload.project_id,payload.experiment_id,payload.budget_id,payload.grant_id,payload.cost_centre_id,payload.equipment_id,payload.inventory_item_id,
                payload.transaction_type,payload.category,payload.description,payload.amount,payload.currency,payload.transaction_date,payload.supplier_name,payload.invoice_reference,payload.recorded_by,payload.source_reference)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, detail={"code": "financial_invoice_reference_exists"}) from exc
            raise
    return dict(row)


@router.get("/transactions")
async def list_transactions(request: Request, project_id: uuid.UUID | None = None, limit: int = Query(100,ge=1,le=500), subject: str = Depends(authenticated_subject)):
    pool = await _pool(request)
    async with pool.acquire() as con:
        rows = await con.fetch(
            """SELECT transaction_id::text,project_id::text,experiment_id::text,budget_id::text,grant_id::text,transaction_type,category,description,amount,currency,transaction_date,supplier_name,invoice_reference,recorded_by,created_at
               FROM lab_financial_transactions WHERE owner_subject=$1 AND ($2::uuid IS NULL OR project_id=$2)
               ORDER BY transaction_date DESC,created_at DESC LIMIT $3""", subject,project_id,limit)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.post("/depreciation", status_code=status.HTTP_201_CREATED)
async def create_depreciation(payload: DepreciationCreate, request: Request, subject: str = Depends(authenticated_subject)):
    if payload.residual_value > payload.acquisition_cost:
        raise HTTPException(422, detail={"code":"residual_exceeds_acquisition_cost"})
    pool=await _pool(request)
    async with pool.acquire() as con:
        try:
            row=await con.fetchrow(
                """INSERT INTO lab_asset_depreciation(owner_subject,equipment_id,acquisition_date,acquisition_cost,currency,useful_life_months,residual_value)
                   SELECT $1,e.equipment_id,$3,$4,$5,$6,$7 FROM lab_equipment e WHERE e.equipment_id=$2 AND e.owner_subject=$1
                   RETURNING depreciation_id::text,equipment_id::text,acquisition_date,acquisition_cost,currency,useful_life_months,residual_value,method,created_at""",
                subject,payload.equipment_id,payload.acquisition_date,payload.acquisition_cost,payload.currency,payload.useful_life_months,payload.residual_value)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409,detail={"code":"equipment_depreciation_exists"}) from exc
            raise
        if row is None:
            raise HTTPException(404,detail={"code":"equipment_not_found"})
    return dict(row)


@router.get("/depreciation")
async def list_depreciation(request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch(
            """SELECT d.depreciation_id::text,d.equipment_id::text,e.name,d.acquisition_date,d.acquisition_cost,d.currency,d.useful_life_months,d.residual_value,
                      ROUND((d.acquisition_cost-d.residual_value)/d.useful_life_months,4) AS monthly_depreciation,
                      GREATEST(0, d.acquisition_cost-d.residual_value) AS depreciable_amount
               FROM lab_asset_depreciation d JOIN lab_equipment e ON e.equipment_id=d.equipment_id
               WHERE d.owner_subject=$1 AND e.owner_subject=$1 ORDER BY d.acquisition_date DESC""",subject)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.get("/analytics")
async def finance_analytics(request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        currencies=await con.fetch(
            """SELECT currency,
                      SUM(CASE WHEN transaction_type='expense' THEN amount WHEN transaction_type='credit' THEN -amount ELSE amount END) AS net_spend,
                      COUNT(*) AS transaction_count
               FROM lab_financial_transactions WHERE owner_subject=$1 GROUP BY currency ORDER BY currency""",subject)
        budgets=await con.fetch(
            """SELECT b.budget_id::text,b.name,b.currency,b.approved_amount,
                      COALESCE(SUM(CASE WHEN t.transaction_type='credit' THEN -t.amount ELSE t.amount END),0) AS actual_spend
               FROM lab_budgets b LEFT JOIN lab_financial_transactions t ON t.budget_id=b.budget_id AND t.owner_subject=b.owner_subject
               WHERE b.owner_subject=$1 GROUP BY b.budget_id ORDER BY b.name""",subject)
        projects=await con.fetch(
            """SELECT p.project_id::text,p.title, t.currency,
                      SUM(CASE WHEN t.transaction_type='credit' THEN -t.amount ELSE t.amount END) AS net_cost,
                      COUNT(t.transaction_id) AS transaction_count
               FROM lab_projects p JOIN lab_financial_transactions t ON t.project_id=p.project_id AND t.owner_subject=p.owner_subject
               WHERE p.owner_subject=$1 GROUP BY p.project_id,t.currency ORDER BY p.title""",subject)
    return {"by_currency":[dict(r) for r in currencies],"budgets":[dict(r) for r in budgets],"project_costs":[dict(r) for r in projects],
            "currency_policy":"Amounts are grouped by currency; no cross-currency totals or implied FX conversions."}
