"""ORIOM7 LAB quality, non-conformance, CAPA and compliance records.

These endpoints provide traceability and management information. They do not
certify laboratory quality, independently verify suppliers or determine legal compliance.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from accessibility import authenticated_subject

router = APIRouter(prefix="/v1/labs/quality", tags=["laboratory-quality-compliance"])


def _clean(value: str) -> str:
    return " ".join(value.split())


async def _pool(request: Request):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(503, detail={"code": "lab_quality_database_unavailable"})
    return pool


class InspectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: uuid.UUID
    inspection_type: str = Field(min_length=2, max_length=100)
    outcome: Literal["pass", "fail", "conditional"]
    sample_size: int = Field(gt=0, le=1000000)
    defects_count: int = Field(default=0, ge=0, le=1000000)
    performed_by: str = Field(min_length=2, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)
    evidence_reference: str | None = Field(default=None, max_length=1000)

    @field_validator("inspection_type", "performed_by")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value

    @field_validator("defects_count")
    @classmethod
    def defect_count_within_sample(cls, value: int, info):
        sample_size = info.data.get("sample_size")
        if sample_size is not None and value > sample_size:
            raise ValueError("defects_count cannot exceed sample_size")
        return value


class NonconformanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)
    severity: Literal["minor", "major", "critical"] = "major"
    assigned_to: str | None = Field(default=None, max_length=160)
    due_date: date | None = None

    @field_validator("title", "description")
    @classmethod
    def clean_nonconformance_text(cls, value: str) -> str:
        value = _clean(value)
        if len(value) < 3:
            raise ValueError("field must contain at least three non-space characters")
        return value


class CapaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nonconformance_id: uuid.UUID
    action_type: Literal["correction", "corrective", "preventive"]
    description: str = Field(min_length=3, max_length=4000)
    assigned_to: str = Field(min_length=2, max_length=160)
    due_date: date | None = None
    recorded_by: str = Field(min_length=2, max_length=160)

    @field_validator("description", "assigned_to", "recorded_by")
    @classmethod
    def clean_capa_text(cls, value: str) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value


class CapaStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["planned", "in_progress", "completed", "verified"]
    recorded_by: str = Field(min_length=2, max_length=160)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("recorded_by")
    @classmethod
    def clean_recorder(cls, value: str) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("recorded_by cannot be blank")
        return value


class ComplianceDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: uuid.UUID | None = None
    document_type: str = Field(min_length=2, max_length=100)
    document_name: str = Field(min_length=2, max_length=180)
    reference: str = Field(min_length=2, max_length=1000)
    issued_at: date | None = None
    expires_at: date | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("document_type", "document_name", "reference")
    @classmethod
    def clean_document_text(cls, value: str) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value

    @field_validator("expires_at")
    @classmethod
    def expiry_after_issue(cls, value: date | None, info):
        issued = info.data.get("issued_at")
        if value and issued and value < issued:
            raise ValueError("expires_at cannot precede issued_at")
        return value


class ComplianceReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_status: Literal["accepted", "rejected", "superseded"]
    reviewed_by: str = Field(min_length=2, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("reviewed_by")
    @classmethod
    def clean_reviewer(cls, value: str) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("reviewed_by cannot be blank")
        return value


@router.post("/inspections", status_code=status.HTTP_201_CREATED)
async def create_inspection(payload: InspectionCreate, request: Request, subject: str = Depends(authenticated_subject)):
    if payload.defects_count > payload.sample_size:
        raise HTTPException(422, detail={"code": "quality_defects_exceed_sample"})
    pool = await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            lot = await con.fetchrow(
                """SELECT l.lot_id,l.item_id,l.lot_code,l.inspection_status,i.sku,i.name
                   FROM lab_inventory_lots l JOIN lab_inventory_items i ON i.item_id=l.item_id AND i.owner_subject=l.owner_subject
                   WHERE l.lot_id=$1 AND l.owner_subject=$2 FOR UPDATE OF l""", payload.lot_id, subject)
            if lot is None:
                raise HTTPException(404, detail={"code": "inventory_lot_not_found"})
            row = await con.fetchrow(
                """INSERT INTO lab_quality_inspections(lot_id,owner_subject,inspection_type,outcome,sample_size,defects_count,performed_by,notes,evidence_reference)
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
                   RETURNING inspection_id::text,lot_id::text,inspection_type,outcome,sample_size,defects_count,performed_by,notes,evidence_reference,inspected_at""",
                payload.lot_id,subject,payload.inspection_type,payload.outcome,payload.sample_size,payload.defects_count,payload.performed_by,payload.notes,payload.evidence_reference)
            ncr = None
            if payload.outcome in ("fail", "conditional"):
                await con.execute(
                    "UPDATE lab_inventory_lots SET inspection_status='quarantined' WHERE lot_id=$1 AND owner_subject=$2",
                    payload.lot_id, subject)
            else:
                # A passing, recorded quality inspection is the release decision for this lot.
                await con.execute(
                    "UPDATE lab_inventory_lots SET inspection_status='accepted' WHERE lot_id=$1 AND owner_subject=$2",
                    payload.lot_id, subject)
                ncr = await con.fetchrow(
                    """INSERT INTO lab_quality_nonconformances(owner_subject,source_inspection_id,title,description,severity)
                       VALUES($1,$2,$3,$4,$5) RETURNING nonconformance_id::text,status,severity""",
                    subject,uuid.UUID(row["inspection_id"]),f"{payload.outcome.title()} inspection: {lot['sku']} / {lot['lot_code']}",
                    payload.notes or f"Inspection outcome was {payload.outcome}; investigate before release.", "major" if payload.outcome=="fail" else "minor")
    return {"inspection":dict(row),"nonconformance":dict(ncr) if ncr else None,"lot_status":"quarantined" if ncr else "accepted"}


@router.get("/inspections")
async def list_inspections(request: Request, limit: int = Query(100,ge=1,le=300), subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch(
            """SELECT q.inspection_id::text,q.lot_id::text,l.lot_code,i.sku,i.name,q.inspection_type,q.outcome,q.sample_size,q.defects_count,q.performed_by,q.notes,q.evidence_reference,q.inspected_at
               FROM lab_quality_inspections q JOIN lab_inventory_lots l ON l.lot_id=q.lot_id AND l.owner_subject=q.owner_subject
               JOIN lab_inventory_items i ON i.item_id=l.item_id AND i.owner_subject=l.owner_subject
               WHERE q.owner_subject=$1 ORDER BY q.inspected_at DESC LIMIT $2""",subject,limit)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.post("/nonconformances", status_code=status.HTTP_201_CREATED)
async def create_nonconformance(payload: NonconformanceCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        row=await con.fetchrow(
            """INSERT INTO lab_quality_nonconformances(owner_subject,title,description,severity,assigned_to,due_date)
               VALUES($1,$2,$3,$4,$5,$6) RETURNING nonconformance_id::text,title,description,severity,status,assigned_to,due_date,created_at""",
            subject,_clean(payload.title),_clean(payload.description),payload.severity,_clean(payload.assigned_to) if payload.assigned_to else None,payload.due_date)
    return dict(row)


@router.get("/nonconformances")
async def list_nonconformances(request: Request, limit: int = Query(100,ge=1,le=300), subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch(
            """SELECT n.nonconformance_id::text,n.title,n.description,n.severity,n.status,n.assigned_to,n.due_date,n.created_at,
                      q.inspection_id::text,l.lot_code
               FROM lab_quality_nonconformances n LEFT JOIN lab_quality_inspections q ON q.inspection_id=n.source_inspection_id AND q.owner_subject=n.owner_subject
               LEFT JOIN lab_inventory_lots l ON l.lot_id=q.lot_id AND l.owner_subject=q.owner_subject
               WHERE n.owner_subject=$1 ORDER BY n.created_at DESC LIMIT $2""",subject,limit)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.post("/capa", status_code=status.HTTP_201_CREATED)
async def create_capa(payload: CapaCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            if not await con.fetchval("SELECT 1 FROM lab_quality_nonconformances WHERE nonconformance_id=$1 AND owner_subject=$2 AND status NOT IN ('closed','verified')",payload.nonconformance_id,subject):
                raise HTTPException(404,detail={"code":"quality_nonconformance_not_found_or_closed"})
            row=await con.fetchrow(
                """INSERT INTO lab_quality_capa_actions(nonconformance_id,owner_subject,action_type,description,assigned_to,due_date)
                   VALUES($1,$2,$3,$4,$5,$6) RETURNING action_id::text,nonconformance_id::text,action_type,description,assigned_to,due_date,status,created_at""",
                payload.nonconformance_id,subject,payload.action_type,_clean(payload.description),_clean(payload.assigned_to),payload.due_date)
            await con.execute(
                """INSERT INTO lab_quality_capa_events(action_id,owner_subject,event_type,to_status,note,recorded_by)
                   VALUES($1,$2,'created','planned',$3,$4)""",
                uuid.UUID(row["action_id"]),subject,_clean(payload.description),_clean(payload.recorded_by))
            await con.execute(
                "UPDATE lab_quality_nonconformances SET status='capa_in_progress',updated_at=now() WHERE nonconformance_id=$1 AND owner_subject=$2",
                payload.nonconformance_id,subject)
    return dict(row)


@router.get("/capa")
async def list_capa(request: Request, limit: int = Query(100,ge=1,le=300), subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch(
            """SELECT a.action_id::text,a.nonconformance_id::text,n.title AS nonconformance_title,a.action_type,a.description,a.assigned_to,a.due_date,a.status,a.created_at
               FROM lab_quality_capa_actions a JOIN lab_quality_nonconformances n ON n.nonconformance_id=a.nonconformance_id AND n.owner_subject=a.owner_subject
               WHERE a.owner_subject=$1 ORDER BY a.created_at DESC LIMIT $2""",subject,limit)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.patch("/capa/{action_id}")
async def update_capa(action_id: uuid.UUID, payload: CapaStatusUpdate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            row=await con.fetchrow(
                """SELECT action_id,status,nonconformance_id FROM lab_quality_capa_actions
                   WHERE action_id=$1 AND owner_subject=$2 FOR UPDATE""",action_id,subject)
            if row is None:
                raise HTTPException(404,detail={"code":"quality_capa_action_not_found"})
            allowed_next = {"planned": "in_progress", "in_progress": "completed", "completed": "verified", "verified": None}
            if payload.status != allowed_next[row["status"]]:
                raise HTTPException(409,detail={"code":"quality_invalid_capa_transition","expected_next_status":allowed_next[row["status"]]})
            updated=await con.fetchrow(
                """UPDATE lab_quality_capa_actions SET status=$2,updated_at=now()
                   WHERE action_id=$1 AND owner_subject=$3
                   RETURNING action_id::text,status,nonconformance_id::text""",action_id,payload.status,subject)
            event_type="verified" if payload.status=="verified" else "status_changed"
            await con.execute(
                """INSERT INTO lab_quality_capa_events(action_id,owner_subject,event_type,from_status,to_status,note,recorded_by)
                   VALUES($1,$2,$3,$4,$5,$6,$7)""",
                action_id,subject,event_type,row["status"],payload.status,payload.note,_clean(payload.recorded_by))
            if payload.status=="verified":
                outstanding=await con.fetchval(
                    "SELECT count(*) FROM lab_quality_capa_actions WHERE nonconformance_id=$1 AND owner_subject=$2 AND status<>'verified'",
                    row["nonconformance_id"],subject)
                if outstanding==0:
                    await con.execute(
                        "UPDATE lab_quality_nonconformances SET status='verified',updated_at=now() WHERE nonconformance_id=$1 AND owner_subject=$2",
                        row["nonconformance_id"],subject)
    return dict(updated)


@router.get("/compliance-documents")
async def list_compliance_documents(request: Request, limit: int = Query(100,ge=1,le=300), subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        rows=await con.fetch(
            """SELECT d.document_id::text,d.supplier_id::text,s.name AS supplier_name,d.document_type,d.document_name,d.reference,d.issued_at,d.expires_at,d.review_status,d.reviewed_by,d.reviewed_at,d.notes,d.created_at,
                      CASE WHEN d.expires_at IS NOT NULL AND d.expires_at<CURRENT_DATE THEN 'expired'
                           WHEN d.expires_at BETWEEN CURRENT_DATE AND CURRENT_DATE+30 THEN 'expiring_soon'
                           ELSE 'not_expired' END AS expiry_state
               FROM lab_compliance_documents d LEFT JOIN lab_inventory_suppliers s ON s.supplier_id=d.supplier_id AND s.owner_subject=d.owner_subject
               WHERE d.owner_subject=$1 ORDER BY d.expires_at NULLS LAST,d.created_at DESC LIMIT $2""",subject,limit)
    return {"items":[dict(r) for r in rows],"total":len(rows)}


@router.post("/compliance-documents", status_code=status.HTTP_201_CREATED)
async def create_compliance_document(payload: ComplianceDocumentCreate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        if payload.supplier_id and not await con.fetchval("SELECT 1 FROM lab_inventory_suppliers WHERE supplier_id=$1 AND owner_subject=$2",payload.supplier_id,subject):
            raise HTTPException(404,detail={"code":"inventory_supplier_not_found"})
        row=await con.fetchrow(
            """INSERT INTO lab_compliance_documents(owner_subject,supplier_id,document_type,document_name,reference,issued_at,expires_at,notes)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8)
               RETURNING document_id::text,supplier_id::text,document_type,document_name,reference,issued_at,expires_at,review_status,created_at""",
            subject,payload.supplier_id,_clean(payload.document_type),_clean(payload.document_name),_clean(payload.reference),payload.issued_at,payload.expires_at,payload.notes)
    return dict(row)


@router.patch("/compliance-documents/{document_id}/review")
async def review_compliance_document(document_id: uuid.UUID, payload: ComplianceReviewUpdate, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        row=await con.fetchrow(
            """UPDATE lab_compliance_documents SET review_status=$3,reviewed_by=$4,reviewed_at=now(),notes=COALESCE($5,notes)
               WHERE document_id=$1 AND owner_subject=$2 AND review_status='pending_review'
               RETURNING document_id::text,review_status,reviewed_by,reviewed_at,expires_at""",
            document_id,subject,payload.review_status,_clean(payload.reviewed_by),payload.notes)
    if row is None:
        raise HTTPException(404,detail={"code":"quality_document_not_found_or_already_reviewed"})
    return dict(row)


@router.get("/analytics")
async def quality_analytics(request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        row=await con.fetchrow(
            """SELECT
                 (SELECT count(*)::int FROM lab_quality_inspections WHERE owner_subject=$1) AS total_inspections,
                 (SELECT count(*)::int FROM lab_quality_inspections WHERE owner_subject=$1 AND outcome='pass') AS passed_inspections,
                 (SELECT count(*)::int FROM lab_quality_inspections WHERE owner_subject=$1 AND outcome='fail') AS failed_inspections,
                 (SELECT count(*)::int FROM lab_quality_inspections WHERE owner_subject=$1 AND outcome='conditional') AS conditional_inspections,
                 (SELECT count(*)::int FROM lab_quality_nonconformances WHERE owner_subject=$1 AND status NOT IN ('verified','closed')) AS open_nonconformances,
                 (SELECT count(*)::int FROM lab_quality_capa_actions WHERE owner_subject=$1 AND status<>'verified') AS open_capa_actions,
                 (SELECT count(*)::int FROM lab_quality_capa_actions WHERE owner_subject=$1 AND due_date<CURRENT_DATE AND status<>'verified') AS overdue_capa_actions,
                 (SELECT count(*)::int FROM lab_compliance_documents WHERE owner_subject=$1 AND review_status='pending_review') AS documents_pending_review,
                 (SELECT count(*)::int FROM lab_compliance_documents WHERE owner_subject=$1 AND expires_at<CURRENT_DATE) AS expired_documents,
                 (SELECT count(*)::int FROM lab_compliance_documents WHERE owner_subject=$1 AND expires_at BETWEEN CURRENT_DATE AND CURRENT_DATE+30) AS documents_expiring_30_days""",subject)
        suppliers=await con.fetch(
            """SELECT s.supplier_id::text,s.name,
                 count(q.inspection_id)::int AS inspections,
                 count(q.inspection_id) FILTER(WHERE q.outcome='pass')::int AS passed,
                 count(q.inspection_id) FILTER(WHERE q.outcome='fail')::int AS failed,
                 count(q.inspection_id) FILTER(WHERE q.outcome='conditional')::int AS conditional,
                 CASE WHEN count(q.inspection_id)=0 THEN NULL ELSE round(100.0*count(q.inspection_id) FILTER(WHERE q.outcome='pass')/count(q.inspection_id),1) END AS pass_rate_percent
               FROM lab_inventory_suppliers s
               LEFT JOIN lab_inventory_lots l ON l.supplier_id=s.supplier_id AND l.owner_subject=s.owner_subject
               LEFT JOIN lab_quality_inspections q ON q.lot_id=l.lot_id AND q.owner_subject=l.owner_subject
               WHERE s.owner_subject=$1 GROUP BY s.supplier_id,s.name ORDER BY failed DESC,pass_rate_percent ASC NULLS LAST,s.name""",subject)
    return {"metrics":dict(row),"supplier_quality": [dict(r) for r in suppliers]}


@router.get("/capa/{action_id}/events")
async def list_capa_events(action_id: uuid.UUID, request: Request, subject: str = Depends(authenticated_subject)):
    pool=await _pool(request)
    async with pool.acquire() as con:
        exists=await con.fetchval("SELECT 1 FROM lab_quality_capa_actions WHERE action_id=$1 AND owner_subject=$2",action_id,subject)
        if not exists:
            raise HTTPException(404,detail={"code":"quality_capa_action_not_found"})
        rows=await con.fetch(
            """SELECT event_id::text,event_type,from_status,to_status,note,recorded_by,created_at
               FROM lab_quality_capa_events WHERE action_id=$1 AND owner_subject=$2 ORDER BY created_at,event_id""",action_id,subject)
    return {"items":[dict(r) for r in rows],"total":len(rows)}
