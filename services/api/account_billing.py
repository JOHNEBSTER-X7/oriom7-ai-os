"""Authenticated ORIOM7 account and billing-readiness APIs."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from accessibility import authenticated_subject

router = APIRouter(prefix="/v1/account", tags=["account-billing"])
PLANS = [
 {"plan_code":"starter","name":"Starter","price_minor":0,"currency":"USD","monthly_request_limit":1000,"availability":"development"},
 {"plan_code":"builder","name":"Builder","price_minor":None,"currency":"USD","monthly_request_limit":25000,"availability":"pricing_pending"},
 {"plan_code":"business","name":"Business","price_minor":None,"currency":"USD","monthly_request_limit":250000,"availability":"pricing_pending"},
 {"plan_code":"enterprise","name":"Enterprise","price_minor":None,"currency":"USD","monthly_request_limit":None,"availability":"contact_required"},
]
class AccountUpdate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 display_name:str|None=Field(default=None,max_length=100)
class OrganisationCreate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 name:str=Field(min_length=2,max_length=120)
 slug:str=Field(min_length=3,max_length=60,pattern=r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$")

async def _pool(request:Request):
 pool=getattr(request.app.state,"database_pool",None)
 if pool is None: raise HTTPException(503,detail={"code":"account_database_unavailable"})
 return pool

async def _account(con,subject):
 return await con.fetchrow("""INSERT INTO oriom7_accounts(subject_id) VALUES($1)
 ON CONFLICT(subject_id) DO UPDATE SET updated_at=NOW()
 RETURNING account_id::text,subject_id,display_name,created_at,updated_at""",subject)

@router.get("/profile")
async def get_profile(request:Request,subject:str=Depends(authenticated_subject)):
 pool=await _pool(request)
 async with pool.acquire() as con: row=await _account(con,subject)
 return {"account":dict(row),"identity_provider":"deployment_managed","authentication_status":"authenticated"}

@router.patch("/profile")
async def update_profile(payload:AccountUpdate,request:Request,subject:str=Depends(authenticated_subject)):
 pool=await _pool(request)
 async with pool.acquire() as con:
  await _account(con,subject)
  row=await con.fetchrow("""UPDATE oriom7_accounts SET display_name=$2,updated_at=NOW()
   WHERE subject_id=$1 RETURNING account_id::text,subject_id,display_name,created_at,updated_at""",subject,payload.display_name)
 return {"account":dict(row)}

@router.get("/plans")
async def list_plans():
 return {"plans":PLANS,"billing_status":"not_configured","checkout_enabled":False}

@router.get("/subscription")
async def get_subscription(request:Request,subject:str=Depends(authenticated_subject)):
 pool=await _pool(request)
 async with pool.acquire() as con:
  account=await _account(con,subject)
  row=await con.fetchrow("""SELECT subscription_id::text,plan_code,status,provider,current_period_start,current_period_end
   FROM oriom7_subscriptions WHERE account_id=$1::uuid ORDER BY created_at DESC LIMIT 1""",account["account_id"])
 if row is None: return {"subscription":None,"billing_status":"not_configured","message":"No paid subscription is active. Checkout is disabled until a payment provider is configured."}
 item=dict(row)
 for key in ("current_period_start","current_period_end"):
  if item[key] is not None: item[key]=item[key].isoformat()
 return {"subscription":item,"billing_status":"not_configured" if item["status"]=="not_configured" else "provider_managed"}

@router.get("/invoices")
async def list_invoices(request:Request,subject:str=Depends(authenticated_subject)):
 pool=await _pool(request)
 async with pool.acquire() as con:
  account=await _account(con,subject)
  rows=await con.fetch("""SELECT invoice_id::text,invoice_number,currency,amount_due_minor,amount_paid_minor,status,
   hosted_invoice_url,issued_at,due_at FROM oriom7_invoices WHERE account_id=$1::uuid ORDER BY created_at DESC LIMIT 100""",account["account_id"])
 items=[]
 for row in rows:
  item=dict(row)
  for key in ("issued_at","due_at"):
   if item[key] is not None: item[key]=item[key].isoformat()
  items.append(item)
 return {"invoices":items,"billing_status":"not_configured"}

@router.post("/organisations",status_code=201)
async def create_organisation(payload:OrganisationCreate,request:Request,subject:str=Depends(authenticated_subject)):
 pool=await _pool(request)
 async with pool.acquire() as con:
  async with con.transaction():
   await _account(con,subject)
   try:
    row=await con.fetchrow("""INSERT INTO oriom7_organisations(name,slug,created_by_subject)
     VALUES($1,$2,$3) RETURNING organisation_id::text,name,slug,created_at""",payload.name.strip(),payload.slug,subject)
   except Exception as exc:
    if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
     raise HTTPException(409,detail={"code":"organisation_slug_taken"}) from exc
    raise
   await con.execute("""INSERT INTO oriom7_organisation_members(organisation_id,subject_id,role)
    VALUES($1::uuid,$2,'owner')""",row["organisation_id"],subject)
 return {"organisation":dict(row),"membership_role":"owner"}

@router.get("/organisations")
async def list_organisations(request:Request,subject:str=Depends(authenticated_subject)):
 pool=await _pool(request)
 async with pool.acquire() as con:
  rows=await con.fetch("""SELECT o.organisation_id::text,o.name,o.slug,m.role,o.created_at
   FROM oriom7_organisations o JOIN oriom7_organisation_members m ON m.organisation_id=o.organisation_id
   WHERE m.subject_id=$1 ORDER BY o.created_at DESC""",subject)
 return {"organisations":[dict(row) for row in rows]}

@router.get("/usage")
async def get_usage(request:Request,subject:str=Depends(authenticated_subject)):
 pool=await _pool(request)
 async with pool.acquire() as con:
  account=await _account(con,subject)
  rows=await con.fetch("""SELECT product_code,COUNT(*)::bigint AS events,COALESCE(SUM(quantity),0)::bigint AS units
   FROM oriom7_usage_ledger WHERE account_id=$1::uuid AND occurred_at>=date_trunc('month',NOW())
   GROUP BY product_code ORDER BY product_code""",account["account_id"])
 return {"period":"current_calendar_month","usage":[dict(row) for row in rows],"billing_status":"not_configured"}
