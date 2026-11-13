"""ORIOM7 LAB OS: authenticated research projects, experiments and equipment registry.

This is a digital research-management foundation. It does not control laboratory
hardware, certify experiments, or replace local safety and quality systems.
"""
from __future__ import annotations

import json
import uuid
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
        row = await con.fetchrow(
            """UPDATE lab_equipment SET status=$3, updated_at=now()
               WHERE equipment_id=$1 AND owner_subject=$2
               RETURNING equipment_id::text, name, category, manufacturer, model,
                         asset_tag, location, status, metadata, created_at, updated_at""",
            equipment_id, subject, payload.status,
        )
    if row is None:
        raise HTTPException(404, detail={"code": "lab_equipment_not_found"})
    return _equipment(row)
