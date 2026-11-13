"""ORIOM7 LAB OS: authenticated research projects, experiments and equipment registry.

This is a digital research-management foundation. It does not control laboratory
hardware, certify experiments, or replace local safety and quality systems.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from accessibility import authenticated_subject

router = APIRouter(prefix="/v1/labs", tags=["laboratory-operations"])

ProjectDiscipline = Literal[
    "ai", "semiconductors", "computing", "robotics", "automotive",
    "networking", "cybersecurity", "materials", "energy", "aerospace",
    "biotechnology", "healthcare", "manufacturing", "agriculture",
    "mining", "fintech", "commerce", "other",
]
ProjectStatus = Literal["planning", "active", "paused", "completed", "archived"]
ExperimentStatus = Literal["planned", "queued", "running", "completed", "failed", "cancelled"]
EquipmentStatus = Literal["available", "in_use", "maintenance", "retired"]
EventType = Literal[
    "note", "protocol_update", "status_change", "measurement",
    "result_summary", "deviation", "review",
]


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _json_size(value: dict[str, Any]) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError("data must be JSON serialisable and cannot contain NaN or infinity") from exc


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    discipline: ProjectDiscipline = "other"
    objectives: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = _clean_text(value)
        if len(value) < 3:
            raise ValueError("title must contain at least three non-space characters")
        return value

    @field_validator("objectives")
    @classmethod
    def clean_objectives(cls, values: list[str]) -> list[str]:
        cleaned = [_clean_text(v) for v in values]
        if any(not v or len(v) > 500 for v in cleaned):
            raise ValueError("each objective must contain 1 to 500 characters")
        return list(dict.fromkeys(cleaned))


class ProjectStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ProjectStatus


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=160)
    hypothesis: str | None = Field(default=None, max_length=4000)
    protocol: str | None = Field(default=None, max_length=12000)
    configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = _clean_text(value)
        if len(value) < 3:
            raise ValueError("title must contain at least three non-space characters")
        return value

    @field_validator("configuration")
    @classmethod
    def bounded_configuration(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _json_size(value) > 16000:
            raise ValueError("configuration must not exceed 16 KB")
        return value


class ExperimentEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: EventType
    summary: str = Field(min_length=3, max_length=1000)
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        value = _clean_text(value)
        if len(value) < 3:
            raise ValueError("summary must contain at least three non-space characters")
        return value

    @field_validator("data")
    @classmethod
    def bounded_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _json_size(value) > 16000:
            raise ValueError("event data must not exceed 16 KB")
        return value


class EquipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    manufacturer: str | None = Field(default=None, max_length=160)
    model: str | None = Field(default=None, max_length=160)
    asset_tag: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "category")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = _clean_text(value)
        if len(value) < 2:
            raise ValueError("field must contain at least two non-space characters")
        return value

    @field_validator("metadata")
    @classmethod
    def bounded_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _json_size(value) > 16000:
            raise ValueError("metadata must not exceed 16 KB")
        return value


class EquipmentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: EquipmentStatus


async def _pool(request: Request):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "lab_database_unavailable", "message": "Persistent laboratory storage is not configured."},
        )
    return pool


def _project(row: Any) -> dict[str, Any]:
    objectives = row["objectives"]
    if isinstance(objectives, str):
        objectives = json.loads(objectives)
    return {
        "project_id": row["project_id"],
        "title": row["title"],
        "description": row["description"],
        "discipline": row["discipline"],
        "objectives": objectives,
        "status": row["status"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _experiment(row: Any) -> dict[str, Any]:
    configuration = row["configuration"]
    if isinstance(configuration, str):
        configuration = json.loads(configuration)
    return {
        "experiment_id": row["experiment_id"],
        "project_id": row["project_id"],
        "title": row["title"],
        "hypothesis": row["hypothesis"],
        "protocol": row["protocol"],
        "configuration": configuration,
        "status": row["status"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _equipment(row: Any) -> dict[str, Any]:
    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return {
        "equipment_id": row["equipment_id"],
        "name": row["name"],
        "category": row["category"],
        "manufacturer": row["manufacturer"],
        "model": row["model"],
        "asset_tag": row["asset_tag"],
        "location": row["location"],
        "status": row["status"],
        "metadata": metadata,
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    project_id = str(uuid.uuid4())
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """INSERT INTO lab_projects
               (project_id, owner_subject, title, description, discipline, objectives)
               VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb)
               RETURNING project_id::text, title, description, discipline, objectives,
                         status, created_at, updated_at""",
            project_id, subject, payload.title, payload.description,
            payload.discipline, json.dumps(payload.objectives),
        )
    return _project(row)


@router.get("/projects")
async def list_projects(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    discipline: ProjectDiscipline | None = None,
    project_status: ProjectStatus | None = Query(default=None, alias="status"),
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        rows = await con.fetch(
            """SELECT project_id::text, title, description, discipline, objectives,
                      status, created_at, updated_at
               FROM lab_projects
               WHERE owner_subject=$1
                 AND ($2::text IS NULL OR discipline=$2)
                 AND ($3::text IS NULL OR status=$3)
               ORDER BY updated_at DESC LIMIT $4 OFFSET $5""",
            subject, discipline, project_status, limit, offset,
        )
        total = await con.fetchval(
            """SELECT count(*) FROM lab_projects
               WHERE owner_subject=$1
                 AND ($2::text IS NULL OR discipline=$2)
                 AND ($3::text IS NULL OR status=$3)""",
            subject, discipline, project_status,
        )
    return {"items": [_project(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/projects/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """SELECT project_id::text, title, description, discipline, objectives,
                      status, created_at, updated_at
               FROM lab_projects WHERE project_id=$1 AND owner_subject=$2""",
            project_id, subject,
        )
    if row is None:
        raise HTTPException(404, detail={"code": "lab_project_not_found"})
    return _project(row)


@router.patch("/projects/{project_id}")
async def update_project_status(
    project_id: uuid.UUID,
    payload: ProjectStatusUpdate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """UPDATE lab_projects SET status=$3, updated_at=now()
               WHERE project_id=$1 AND owner_subject=$2
               RETURNING project_id::text, title, description, discipline, objectives,
                         status, created_at, updated_at""",
            project_id, subject, payload.status,
        )
    if row is None:
        raise HTTPException(404, detail={"code": "lab_project_not_found"})
    return _project(row)


@router.post("/projects/{project_id}/experiments", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    project_id: uuid.UUID,
    payload: ExperimentCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    experiment_id = str(uuid.uuid4())
    async with pool.acquire() as con:
        async with con.transaction():
            project = await con.fetchrow(
                "SELECT project_id FROM lab_projects WHERE project_id=$1 AND owner_subject=$2",
                project_id, subject,
            )
            if project is None:
                raise HTTPException(404, detail={"code": "lab_project_not_found"})
            row = await con.fetchrow(
                """INSERT INTO lab_experiments
                   (experiment_id, project_id, owner_subject, title, hypothesis, protocol, configuration)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7::jsonb)
                   RETURNING experiment_id::text, project_id::text, title, hypothesis,
                             protocol, configuration, status, created_at, updated_at""",
                experiment_id, project_id, subject, payload.title, payload.hypothesis,
                payload.protocol, json.dumps(payload.configuration, allow_nan=False),
            )
    return _experiment(row)


@router.get("/projects/{project_id}/experiments")
async def list_experiments(
    project_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        exists = await con.fetchval(
            "SELECT 1 FROM lab_projects WHERE project_id=$1 AND owner_subject=$2",
            project_id, subject,
        )
        if not exists:
            raise HTTPException(404, detail={"code": "lab_project_not_found"})
        rows = await con.fetch(
            """SELECT experiment_id::text, project_id::text, title, hypothesis, protocol,
                      configuration, status, created_at, updated_at
               FROM lab_experiments WHERE project_id=$1 AND owner_subject=$2
               ORDER BY updated_at DESC LIMIT $3 OFFSET $4""",
            project_id, subject, limit, offset,
        )
        total = await con.fetchval(
            "SELECT count(*) FROM lab_experiments WHERE project_id=$1 AND owner_subject=$2",
            project_id, subject,
        )
    return {"items": [_experiment(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: uuid.UUID,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """SELECT experiment_id::text, project_id::text, title, hypothesis, protocol,
                      configuration, status, created_at, updated_at
               FROM lab_experiments WHERE experiment_id=$1 AND owner_subject=$2""",
            experiment_id, subject,
        )
    if row is None:
        raise HTTPException(404, detail={"code": "lab_experiment_not_found"})
    return _experiment(row)


@router.post("/experiments/{experiment_id}/events", status_code=status.HTTP_201_CREATED)
async def append_experiment_event(
    experiment_id: uuid.UUID,
    payload: ExperimentEventCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    allowed_transitions = {
        "planned": {"queued", "cancelled"},
        "queued": {"running", "cancelled"},
        "running": {"completed", "failed", "cancelled"},
        "completed": set(),
        "failed": set(),
        "cancelled": set(),
    }
    async with pool.acquire() as con:
        async with con.transaction():
            experiment = await con.fetchrow(
                """SELECT status FROM lab_experiments
                   WHERE experiment_id=$1 AND owner_subject=$2 FOR UPDATE""",
                experiment_id, subject,
            )
            if experiment is None:
                raise HTTPException(404, detail={"code": "lab_experiment_not_found"})
            new_status = None
            if payload.event_type == "status_change":
                new_status = payload.data.get("status")
                if new_status not in ExperimentStatus.__args__:
                    raise HTTPException(422, detail={"code": "invalid_experiment_status"})
                if new_status not in allowed_transitions[experiment["status"]]:
                    raise HTTPException(
                        409,
                        detail={
                            "code": "invalid_experiment_status_transition",
                            "current_status": experiment["status"],
                            "requested_status": new_status,
                        },
                    )
            event_id = str(uuid.uuid4())
            row = await con.fetchrow(
                """INSERT INTO lab_experiment_events
                   (event_id, experiment_id, owner_subject, event_type, summary, data)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb)
                   RETURNING event_id::text, event_type, summary, data, created_at""",
                event_id, experiment_id, subject, payload.event_type, payload.summary,
                json.dumps(payload.data, allow_nan=False),
            )
            if new_status is not None:
                await con.execute(
                    "UPDATE lab_experiments SET status=$2, updated_at=now() WHERE experiment_id=$1",
                    experiment_id, new_status,
                )
    data = row["data"]
    if isinstance(data, str):
        data = json.loads(data)
    return {
        "event_id": row["event_id"],
        "experiment_id": str(experiment_id),
        "event_type": row["event_type"],
        "summary": row["summary"],
        "data": data,
        "created_at": row["created_at"].isoformat(),
        "experiment_status": new_status or experiment["status"],
    }


@router.get("/experiments/{experiment_id}/events")
async def list_experiment_events(
    experiment_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        exists = await con.fetchval(
            "SELECT 1 FROM lab_experiments WHERE experiment_id=$1 AND owner_subject=$2",
            experiment_id, subject,
        )
        if not exists:
            raise HTTPException(404, detail={"code": "lab_experiment_not_found"})
        rows = await con.fetch(
            """SELECT event_id::text, event_type, summary, data, created_at
               FROM lab_experiment_events
               WHERE experiment_id=$1 AND owner_subject=$2
               ORDER BY created_at ASC LIMIT $3 OFFSET $4""",
            experiment_id, subject, limit, offset,
        )
        total = await con.fetchval(
            "SELECT count(*) FROM lab_experiment_events WHERE experiment_id=$1 AND owner_subject=$2",
            experiment_id, subject,
        )
    items = []
    for row in rows:
        data = row["data"]
        if isinstance(data, str):
            data = json.loads(data)
        items.append({
            "event_id": row["event_id"], "event_type": row["event_type"],
            "summary": row["summary"], "data": data,
            "created_at": row["created_at"].isoformat(),
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/equipment", status_code=status.HTTP_201_CREATED)
async def register_equipment(
    payload: EquipmentCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    equipment_id = str(uuid.uuid4())
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """INSERT INTO lab_equipment
               (equipment_id, owner_subject, name, category, manufacturer, model,
                asset_tag, location, metadata)
               VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
               RETURNING equipment_id::text, name, category, manufacturer, model,
                         asset_tag, location, status, metadata, created_at, updated_at""",
            equipment_id, subject, payload.name, payload.category, payload.manufacturer,
            payload.model, payload.asset_tag, payload.location,
            json.dumps(payload.metadata, allow_nan=False),
        )
    return _equipment(row)


@router.get("/equipment")
async def list_equipment(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    equipment_status: EquipmentStatus | None = Query(default=None, alias="status"),
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        rows = await con.fetch(
            """SELECT equipment_id::text, name, category, manufacturer, model, asset_tag,
                      location, status, metadata, created_at, updated_at
               FROM lab_equipment WHERE owner_subject=$1
                 AND ($2::text IS NULL OR status=$2)
               ORDER BY name LIMIT $3 OFFSET $4""",
            subject, equipment_status, limit, offset,
        )
        total = await con.fetchval(
            """SELECT count(*) FROM lab_equipment WHERE owner_subject=$1
               AND ($2::text IS NULL OR status=$2)""",
            subject, equipment_status,
        )
    return {"items": [_equipment(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.patch("/equipment/{equipment_id}")
async def update_equipment_status(
    equipment_id: uuid.UUID,
    payload: EquipmentStatusUpdate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            equipment = await con.fetchrow(
                "SELECT equipment_id FROM lab_equipment WHERE equipment_id=$1 AND owner_subject=$2 FOR UPDATE",
                equipment_id, subject,
            )
            if equipment is None:
                raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
            if payload.status in {"available", "in_use"}:
                latest_calibration = await con.fetchrow(
                    """SELECT outcome, due_on FROM lab_equipment_calibrations
                       WHERE equipment_id=$1 AND owner_subject=$2
                       ORDER BY calibrated_on DESC, created_at DESC LIMIT 1""",
                    equipment_id, subject,
                )
                if latest_calibration and (
                    latest_calibration["outcome"] in {"fail", "conditional"}
                    or (latest_calibration["due_on"] is not None and latest_calibration["due_on"] < date.today())
                ):
                    raise HTTPException(409, detail={"code": "lab_equipment_calibration_block"})
            if payload.status in {"maintenance", "retired"}:
                active_booking = await con.fetchval(
                    """SELECT 1 FROM lab_equipment_bookings
                       WHERE equipment_id=$1 AND owner_subject=$2
                         AND status='confirmed' AND ends_at > now() LIMIT 1""",
                    equipment_id, subject,
                )
                if active_booking:
                    raise HTTPException(409, detail={"code": "lab_equipment_has_active_bookings"})
            row = await con.fetchrow(
                """UPDATE lab_equipment SET status=$3, updated_at=now()
                   WHERE equipment_id=$1 AND owner_subject=$2
                   RETURNING equipment_id::text, name, category, manufacturer, model,
                             asset_tag, location, status, metadata, created_at, updated_at""",
                equipment_id, subject, payload.status,
            )
    return _equipment(row)


# ORIOM7 DIGITAL NOTEBOOK -----------------------------------------------------
NotebookEntryType = Literal[
    "note", "hypothesis", "observation", "measurement", "result",
    "decision", "protocol", "review", "deviation",
]


class NotebookEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry_type: NotebookEntryType
    title: str = Field(min_length=3, max_length=180)
    content: str = Field(min_length=1, max_length=20000)
    experiment_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def clean_notebook_title(cls, value: str) -> str:
        value = _clean_text(value)
        if len(value) < 3:
            raise ValueError("title must contain at least three non-space characters")
        return value

    @field_validator("content")
    @classmethod
    def validate_notebook_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content cannot be blank")
        return value

    @field_validator("metadata")
    @classmethod
    def bound_notebook_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _json_size(value) > 16000:
            raise ValueError("metadata must not exceed 16 KB")
        return value


def _notebook_entry(row: Any) -> dict[str, Any]:
    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return {
        "entry_id": row["entry_id"],
        "project_id": row["project_id"],
        "experiment_id": row["experiment_id"],
        "entry_type": row["entry_type"],
        "title": row["title"],
        "content": row["content"],
        "metadata": metadata,
        "created_at": row["created_at"].isoformat(),
    }


@router.post("/projects/{project_id}/notebook", status_code=status.HTTP_201_CREATED)
async def create_notebook_entry(
    project_id: uuid.UUID,
    payload: NotebookEntryCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    """Append a user-attributed, immutable notebook entry to an owned project."""
    pool = await _pool(request)
    entry_id = str(uuid.uuid4())
    async with pool.acquire() as con:
        async with con.transaction():
            project = await con.fetchrow(
                "SELECT project_id FROM lab_projects WHERE project_id=$1 AND owner_subject=$2",
                project_id, subject,
            )
            if project is None:
                raise HTTPException(404, detail={"code": "lab_project_not_found"})
            if payload.experiment_id is not None:
                experiment = await con.fetchrow(
                    """SELECT experiment_id FROM lab_experiments
                       WHERE experiment_id=$1 AND project_id=$2 AND owner_subject=$3""",
                    payload.experiment_id, project_id, subject,
                )
                if experiment is None:
                    raise HTTPException(404, detail={"code": "lab_experiment_not_found"})
            row = await con.fetchrow(
                """INSERT INTO lab_notebook_entries
                   (entry_id, project_id, experiment_id, owner_subject,
                    entry_type, title, content, metadata)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb)
                   RETURNING entry_id::text, project_id::text, experiment_id::text,
                             entry_type, title, content, metadata, created_at""",
                entry_id, project_id, payload.experiment_id, subject,
                payload.entry_type, payload.title, payload.content,
                json.dumps(payload.metadata, ensure_ascii=False, allow_nan=False),
            )
    return _notebook_entry(row)


@router.get("/projects/{project_id}/notebook")
async def list_notebook_entries(
    project_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    entry_type: NotebookEntryType | None = None,
    experiment_id: uuid.UUID | None = None,
    subject: str = Depends(authenticated_subject),
):
    """Read an owned project's append-only notebook timeline."""
    pool = await _pool(request)
    async with pool.acquire() as con:
        exists = await con.fetchval(
            "SELECT 1 FROM lab_projects WHERE project_id=$1 AND owner_subject=$2",
            project_id, subject,
        )
        if not exists:
            raise HTTPException(404, detail={"code": "lab_project_not_found"})
        if experiment_id is not None:
            experiment_exists = await con.fetchval(
                """SELECT 1 FROM lab_experiments
                   WHERE experiment_id=$1 AND project_id=$2 AND owner_subject=$3""",
                experiment_id, project_id, subject,
            )
            if not experiment_exists:
                raise HTTPException(404, detail={"code": "lab_experiment_not_found"})
        rows = await con.fetch(
            """SELECT entry_id::text, project_id::text, experiment_id::text,
                      entry_type, title, content, metadata, created_at
               FROM lab_notebook_entries
               WHERE project_id=$1 AND owner_subject=$2
                 AND ($3::text IS NULL OR entry_type=$3)
                 AND ($4::uuid IS NULL OR experiment_id=$4)
               ORDER BY created_at ASC, entry_id ASC LIMIT $5 OFFSET $6""",
            project_id, subject, entry_type, experiment_id, limit, offset,
        )
        total = await con.fetchval(
            """SELECT count(*) FROM lab_notebook_entries
               WHERE project_id=$1 AND owner_subject=$2
                 AND ($3::text IS NULL OR entry_type=$3)
                 AND ($4::uuid IS NULL OR experiment_id=$4)""",
            project_id, subject, entry_type, experiment_id,
        )
    return {
        "items": [_notebook_entry(row) for row in rows],
        "total": total, "limit": limit, "offset": offset,
    }


# ORIOM7 EQUIPMENT MANAGER ----------------------------------------------------
CalibrationOutcome = Literal["pass", "fail", "conditional"]
MaintenanceType = Literal["preventive", "corrective", "inspection", "repair", "other"]
BookingStatus = Literal["confirmed", "cancelled", "completed"]


class CalibrationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calibrated_on: date
    due_on: date | None = None
    outcome: CalibrationOutcome
    performed_by: str = Field(min_length=2, max_length=160)
    certificate_reference: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("performed_by")
    @classmethod
    def clean_calibration_performer(cls, value: str) -> str:
        value = _clean_text(value)
        if len(value) < 2:
            raise ValueError("performed_by must contain at least two non-space characters")
        return value

    @field_validator("due_on")
    @classmethod
    def validate_calibration_due_date(cls, value: date | None, info):
        calibrated_on = info.data.get("calibrated_on")
        if value is not None and calibrated_on is not None and value < calibrated_on:
            raise ValueError("due_on cannot precede calibrated_on")
        return value


class MaintenanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    maintenance_type: MaintenanceType
    description: str = Field(min_length=3, max_length=4000)
    performed_by: str = Field(min_length=2, max_length=160)
    performed_at: datetime
    next_due_at: datetime | None = None

    @field_validator("description", "performed_by")
    @classmethod
    def clean_maintenance_text(cls, value: str) -> str:
        value = _clean_text(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value

    @field_validator("performed_at", "next_due_at")
    @classmethod
    def require_timezone(cls, value: datetime | None):
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime must include a timezone")
        return value

    @field_validator("next_due_at")
    @classmethod
    def validate_maintenance_due(cls, value: datetime | None, info):
        performed_at = info.data.get("performed_at")
        if value is not None and performed_at is not None and value < performed_at:
            raise ValueError("next_due_at cannot precede performed_at")
        return value


class EquipmentBookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: str = Field(min_length=3, max_length=1000)
    booked_by: str = Field(min_length=2, max_length=160)
    starts_at: datetime
    ends_at: datetime

    @field_validator("purpose", "booked_by")
    @classmethod
    def clean_booking_text(cls, value: str) -> str:
        value = _clean_text(value)
        if not value:
            raise ValueError("field cannot be blank")
        return value

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_booking_timezone(cls, value: datetime):
        if value.tzinfo is None:
            raise ValueError("datetime must include a timezone")
        return value

    @field_validator("starts_at")
    @classmethod
    def require_future_booking(cls, value: datetime):
        if value <= datetime.now(timezone.utc):
            raise ValueError("starts_at must be in the future")
        return value

    @field_validator("ends_at")
    @classmethod
    def validate_booking_window(cls, value: datetime, info):
        starts_at = info.data.get("starts_at")
        if starts_at is not None and value <= starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return value


class EquipmentBookingStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["cancelled", "completed"]


def _calibration(row: Any) -> dict[str, Any]:
    return {
        "calibration_id": row["calibration_id"],
        "equipment_id": row["equipment_id"],
        "calibrated_on": row["calibrated_on"].isoformat(),
        "due_on": row["due_on"].isoformat() if row["due_on"] else None,
        "outcome": row["outcome"],
        "performed_by": row["performed_by"],
        "certificate_reference": row["certificate_reference"],
        "notes": row["notes"],
        "created_at": row["created_at"].isoformat(),
    }


def _maintenance(row: Any) -> dict[str, Any]:
    return {
        "maintenance_id": row["maintenance_id"],
        "equipment_id": row["equipment_id"],
        "maintenance_type": row["maintenance_type"],
        "description": row["description"],
        "performed_by": row["performed_by"],
        "performed_at": row["performed_at"].isoformat(),
        "next_due_at": row["next_due_at"].isoformat() if row["next_due_at"] else None,
        "created_at": row["created_at"].isoformat(),
    }


def _booking(row: Any) -> dict[str, Any]:
    return {
        "booking_id": row["booking_id"],
        "equipment_id": row["equipment_id"],
        "purpose": row["purpose"],
        "booked_by": row["booked_by"],
        "starts_at": row["starts_at"].isoformat(),
        "ends_at": row["ends_at"].isoformat(),
        "status": row["status"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@router.post("/equipment/{equipment_id}/calibrations", status_code=status.HTTP_201_CREATED)
async def add_equipment_calibration(
    equipment_id: uuid.UUID,
    payload: CalibrationCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    calibration_id = str(uuid.uuid4())
    async with pool.acquire() as con:
        async with con.transaction():
            equipment = await con.fetchrow(
                "SELECT equipment_id FROM lab_equipment WHERE equipment_id=$1 AND owner_subject=$2 FOR UPDATE",
                equipment_id, subject,
            )
            if equipment is None:
                raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
            if payload.outcome in {"fail", "conditional"}:
                # A failed calibration removes the asset from normal availability
                # and cancels its future confirmed reservations.
                await con.execute(
                    "UPDATE lab_equipment SET status='maintenance', updated_at=now() WHERE equipment_id=$1 AND owner_subject=$2",
                    equipment_id, subject,
                )
                await con.execute(
                    """UPDATE lab_equipment_bookings SET status='cancelled', updated_at=now()
                       WHERE equipment_id=$1 AND owner_subject=$2
                         AND status='confirmed' AND ends_at > now()""",
                    equipment_id, subject,
                )
            row = await con.fetchrow(
                """INSERT INTO lab_equipment_calibrations
                   (calibration_id, equipment_id, owner_subject, calibrated_on, due_on,
                    outcome, performed_by, certificate_reference, notes)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9)
                   RETURNING calibration_id::text, equipment_id::text, calibrated_on,
                             due_on, outcome, performed_by, certificate_reference, notes, created_at""",
                calibration_id, equipment_id, subject, payload.calibrated_on, payload.due_on,
                payload.outcome, payload.performed_by, payload.certificate_reference, payload.notes,
            )
    return _calibration(row)


@router.get("/equipment/{equipment_id}/calibrations")
async def list_equipment_calibrations(
    equipment_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        exists = await con.fetchval(
            "SELECT 1 FROM lab_equipment WHERE equipment_id=$1 AND owner_subject=$2",
            equipment_id, subject,
        )
        if not exists:
            raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
        rows = await con.fetch(
            """SELECT calibration_id::text, equipment_id::text, calibrated_on, due_on,
                      outcome, performed_by, certificate_reference, notes, created_at
               FROM lab_equipment_calibrations WHERE equipment_id=$1 AND owner_subject=$2
               ORDER BY calibrated_on DESC, created_at DESC LIMIT $3 OFFSET $4""",
            equipment_id, subject, limit, offset,
        )
        total = await con.fetchval(
            "SELECT count(*) FROM lab_equipment_calibrations WHERE equipment_id=$1 AND owner_subject=$2",
            equipment_id, subject,
        )
    return {"items": [_calibration(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.post("/equipment/{equipment_id}/maintenance", status_code=status.HTTP_201_CREATED)
async def add_equipment_maintenance(
    equipment_id: uuid.UUID,
    payload: MaintenanceCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    maintenance_id = str(uuid.uuid4())
    async with pool.acquire() as con:
        async with con.transaction():
            equipment = await con.fetchrow(
                "SELECT equipment_id FROM lab_equipment WHERE equipment_id=$1 AND owner_subject=$2 FOR UPDATE",
                equipment_id, subject,
            )
            if equipment is None:
                raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
            row = await con.fetchrow(
                """INSERT INTO lab_equipment_maintenance
                   (maintenance_id, equipment_id, owner_subject, maintenance_type,
                    description, performed_by, performed_at, next_due_at)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8)
                   RETURNING maintenance_id::text, equipment_id::text, maintenance_type,
                             description, performed_by, performed_at, next_due_at, created_at""",
                maintenance_id, equipment_id, subject, payload.maintenance_type,
                payload.description, payload.performed_by, payload.performed_at, payload.next_due_at,
            )
    return _maintenance(row)


@router.get("/equipment/{equipment_id}/maintenance")
async def list_equipment_maintenance(
    equipment_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        exists = await con.fetchval(
            "SELECT 1 FROM lab_equipment WHERE equipment_id=$1 AND owner_subject=$2",
            equipment_id, subject,
        )
        if not exists:
            raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
        rows = await con.fetch(
            """SELECT maintenance_id::text, equipment_id::text, maintenance_type,
                      description, performed_by, performed_at, next_due_at, created_at
               FROM lab_equipment_maintenance WHERE equipment_id=$1 AND owner_subject=$2
               ORDER BY performed_at DESC LIMIT $3 OFFSET $4""",
            equipment_id, subject, limit, offset,
        )
        total = await con.fetchval(
            "SELECT count(*) FROM lab_equipment_maintenance WHERE equipment_id=$1 AND owner_subject=$2",
            equipment_id, subject,
        )
    return {"items": [_maintenance(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.post("/equipment/{equipment_id}/bookings", status_code=status.HTTP_201_CREATED)
async def create_equipment_booking(
    equipment_id: uuid.UUID,
    payload: EquipmentBookingCreate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    booking_id = str(uuid.uuid4())
    async with pool.acquire() as con:
        async with con.transaction():
            equipment = await con.fetchrow(
                """SELECT status FROM lab_equipment
                   WHERE equipment_id=$1 AND owner_subject=$2 FOR UPDATE""",
                equipment_id, subject,
            )
            if equipment is None:
                raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
            if equipment["status"] in {"maintenance", "retired"}:
                raise HTTPException(409, detail={"code": "lab_equipment_unavailable"})
            conflict = await con.fetchval(
                """SELECT 1 FROM lab_equipment_bookings
                   WHERE equipment_id=$1 AND owner_subject=$2 AND status='confirmed'
                     AND starts_at < $4 AND ends_at > $3
                   LIMIT 1""",
                equipment_id, subject, payload.starts_at, payload.ends_at,
            )
            if conflict:
                raise HTTPException(409, detail={"code": "lab_equipment_booking_conflict"})
            row = await con.fetchrow(
                """INSERT INTO lab_equipment_bookings
                   (booking_id, equipment_id, owner_subject, purpose, booked_by, starts_at, ends_at)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)
                   RETURNING booking_id::text, equipment_id::text, purpose, booked_by,
                             starts_at, ends_at, status, created_at, updated_at""",
                booking_id, equipment_id, subject, payload.purpose, payload.booked_by,
                payload.starts_at, payload.ends_at,
            )
    return _booking(row)


@router.get("/equipment/{equipment_id}/bookings")
async def list_equipment_bookings(
    equipment_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        exists = await con.fetchval(
            "SELECT 1 FROM lab_equipment WHERE equipment_id=$1 AND owner_subject=$2",
            equipment_id, subject,
        )
        if not exists:
            raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
        rows = await con.fetch(
            """SELECT booking_id::text, equipment_id::text, purpose, booked_by,
                      starts_at, ends_at, status, created_at, updated_at
               FROM lab_equipment_bookings WHERE equipment_id=$1 AND owner_subject=$2
               ORDER BY starts_at DESC LIMIT $3 OFFSET $4""",
            equipment_id, subject, limit, offset,
        )
        total = await con.fetchval(
            "SELECT count(*) FROM lab_equipment_bookings WHERE equipment_id=$1 AND owner_subject=$2",
            equipment_id, subject,
        )
    return {"items": [_booking(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.patch("/equipment/bookings/{booking_id}")
async def update_equipment_booking_status(
    booking_id: uuid.UUID,
    payload: EquipmentBookingStatusUpdate,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = await _pool(request)
    async with pool.acquire() as con:
        async with con.transaction():
            row = await con.fetchrow(
                """SELECT booking_id::text, equipment_id::text, purpose, booked_by,
                          starts_at, ends_at, status, created_at, updated_at
                   FROM lab_equipment_bookings
                   WHERE booking_id=$1 AND owner_subject=$2 FOR UPDATE""",
                booking_id, subject,
            )
            if row is None:
                raise HTTPException(404, detail={"code": "lab_equipment_booking_not_found"})
            if row["status"] != "confirmed":
                raise HTTPException(409, detail={"code": "lab_equipment_booking_not_active"})
            updated = await con.fetchrow(
                """UPDATE lab_equipment_bookings SET status=$3, updated_at=now()
                   WHERE booking_id=$1 AND owner_subject=$2
                   RETURNING booking_id::text, equipment_id::text, purpose, booked_by,
                             starts_at, ends_at, status, created_at, updated_at""",
                booking_id, subject, payload.status,
            )
    return _booking(updated)


@router.get("/equipment/summary")
async def equipment_manager_summary(
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    """Return owner-scoped equipment health and workload counters."""
    pool = await _pool(request)
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """SELECT
                 count(*)::int AS total_assets,
                 count(*) FILTER (WHERE e.status='available')::int AS available_assets,
                 count(*) FILTER (WHERE e.status='in_use')::int AS in_use_assets,
                 count(*) FILTER (WHERE e.status='maintenance')::int AS maintenance_assets,
                 count(*) FILTER (WHERE e.status='retired')::int AS retired_assets,
                 count(*) FILTER (WHERE latest.outcome IN ('fail','conditional')
                    OR (latest.due_on IS NOT NULL AND latest.due_on < CURRENT_DATE))::int
                    AS calibration_attention_assets,
                 (SELECT count(*)::int FROM lab_equipment_bookings b
                  WHERE b.owner_subject=$1 AND b.status='confirmed' AND b.ends_at > now())
                    AS active_bookings,
                 (SELECT count(*)::int FROM (
                    SELECT DISTINCT ON (m.equipment_id) m.equipment_id, m.next_due_at
                    FROM lab_equipment_maintenance m WHERE m.owner_subject=$1
                    ORDER BY m.equipment_id, m.performed_at DESC
                  ) latest_maintenance
                  WHERE latest_maintenance.next_due_at >= now()
                    AND latest_maintenance.next_due_at < now() + interval '30 days')
                    AS maintenance_due_30_days,
                 (SELECT count(*)::int FROM (
                    SELECT DISTINCT ON (m.equipment_id) m.equipment_id, m.next_due_at
                    FROM lab_equipment_maintenance m WHERE m.owner_subject=$1
                    ORDER BY m.equipment_id, m.performed_at DESC
                  ) latest_maintenance
                  WHERE latest_maintenance.next_due_at < now())
                    AS overdue_maintenance_assets
               FROM lab_equipment e
               LEFT JOIN LATERAL (
                 SELECT c.outcome, c.due_on
                 FROM lab_equipment_calibrations c
                 WHERE c.equipment_id=e.equipment_id AND c.owner_subject=e.owner_subject
                 ORDER BY c.calibrated_on DESC, c.created_at DESC LIMIT 1
               ) latest ON TRUE
               WHERE e.owner_subject=$1""",
            subject,
        )
    return dict(row)
