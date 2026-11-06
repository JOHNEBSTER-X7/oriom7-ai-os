"""Stripe Checkout and verified webhook integration for ORIOM7.

Checkout is unavailable unless secret key, webhook secret and configured Stripe
Price IDs are present. Webhooks are signature-checked and idempotently applied.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from uuid import UUID
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from accessibility import authenticated_subject

router=APIRouter(tags=["billing"])

PLAN_PRICE_ENV={"builder":"ORIOM7_STRIPE_PRICE_BUILDER_MONTHLY","business":"ORIOM7_STRIPE_PRICE_BUSINESS_MONTHLY"}
def stripe_ready():
    return bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_WEBHOOK_SECRET")
                and any(os.getenv(name) for name in PLAN_PRICE_ENV.values()))
def price_id(plan_code:str):
    name=PLAN_PRICE_ENV.get(plan_code)
    return os.getenv(name) if name else None

def _safe_return_url(value:str|None)->str|None:
    if not value:return None
    parsed=urlparse(value)
    if parsed.scheme=="https" and parsed.netloc:return value
    if parsed.scheme=="http" and parsed.hostname in {"localhost","127.0.0.1"}:return value
    return None

async def _stripe_post(path:str,data:dict[str,str],idempotency_key:str|None=None):
    secret=os.getenv("STRIPE_SECRET_KEY")
    if not secret:raise HTTPException(503,detail={"code":"billing_not_configured","message":"Stripe billing is not configured."})
    headers={"Idempotency-Key":idempotency_key} if idempotency_key else {}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response=await client.post("https://api.stripe.com/v1/"+path,data=data,auth=(secret,""),headers=headers)
        payload=response.json()
        if response.is_error:
            raise HTTPException(502,detail={"code":"stripe_request_failed","message":"The payment provider could not complete the request."})
        return payload
    except HTTPException:raise
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(502,detail={"code":"stripe_unavailable","message":"The payment provider is temporarily unavailable."}) from exc

class CheckoutRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    plan_code:str=Field(pattern="^(builder|business)$")
    organisation_id:UUID|None=None

@router.post("/v1/account/checkout")
async def create_checkout_session(body:CheckoutRequest,request:Request,subject:str=Depends(authenticated_subject)):
    if not stripe_ready() or not price_id(body.plan_code):
        raise HTTPException(503,detail={"code":"checkout_not_configured","message":"Checkout is not available until Stripe credentials, webhook secret and this plan's Price ID are configured."})
    success=_safe_return_url(os.getenv("ORIOM7_BILLING_SUCCESS_URL"))
    cancel=_safe_return_url(os.getenv("ORIOM7_BILLING_CANCEL_URL"))
    if not success or not cancel:
        raise HTTPException(503,detail={"code":"billing_return_urls_missing","message":"Configure trusted HTTPS billing success and cancellation URLs."})
    pool=getattr(request.app.state,"database_pool",None)
    if pool is None:raise HTTPException(503,detail="Billing database is unavailable.")
    async with pool.acquire() as con:
        async with con.transaction():
            account=await con.fetchrow("""INSERT INTO oriom7_accounts(subject_id) VALUES($1)
             ON CONFLICT(subject_id) DO UPDATE SET updated_at=NOW()
             RETURNING account_id::text,stripe_customer_id""",subject)
            if body.organisation_id:
                member=await con.fetchrow("""SELECT role FROM oriom7_organisation_members
                 WHERE organisation_id=$1::uuid AND subject_id=$2""",body.organisation_id,subject)
                if member is None or member["role"] not in ("owner","admin"):
                    raise HTTPException(403,detail={"code":"billing_permission_denied","message":"Only organisation owners or admins can start checkout."})
    customer=account["stripe_customer_id"]
    if not customer:
        created=await _stripe_post("customers",{"metadata[oriom7_account_id]":account["account_id"],"metadata[oriom7_subject_id]":subject},
                                   "oriom7-customer-"+account["account_id"])
        customer=created.get("id")
        if not customer:raise HTTPException(502,detail="Stripe did not return a customer identifier.")
        async with pool.acquire() as con:
            await con.execute("""UPDATE oriom7_accounts SET stripe_customer_id=$2,updated_at=NOW()
             WHERE account_id=$1::uuid AND stripe_customer_id IS NULL""",account["account_id"],customer)
            current=await con.fetchval("SELECT stripe_customer_id FROM oriom7_accounts WHERE account_id=$1::uuid",account["account_id"])
            customer=current or customer
    data={
      "mode":"subscription","customer":customer,"success_url":success,"cancel_url":cancel,
      "client_reference_id":account["account_id"],"line_items[0][price]":price_id(body.plan_code),
      "line_items[0][quantity]":"1","metadata[oriom7_account_id]":account["account_id"],
      "metadata[oriom7_plan_code]":body.plan_code,
      "subscription_data[metadata][oriom7_account_id]":account["account_id"],
      "subscription_data[metadata][oriom7_plan_code]":body.plan_code,
    }
    if body.organisation_id:
        data["metadata[oriom7_organisation_id]"]=str(body.organisation_id)
        data["subscription_data[metadata][oriom7_organisation_id]"]=str(body.organisation_id)
    session=await _stripe_post("checkout/sessions",data,"oriom7-checkout-"+account["account_id"]+"-"+body.plan_code+"-"+str(int(time.time())//60))
    if not session.get("url"):raise HTTPException(502,detail="Stripe did not return a checkout URL.")
    return {"checkout_url":session["url"],"session_id":session.get("id"),"provider":"stripe","plan_code":body.plan_code}

def _verify_signature(payload:bytes,header:str,secret:str)->bool:
    parts={}
    for part in header.split(","):
        if "=" in part:
            key,value=part.split("=",1)
            parts.setdefault(key,[]).append(value)
    try:timestamp=int(parts["t"][0])
    except (KeyError,ValueError,IndexError):return False
    if abs(time.time()-timestamp)>300:return False
    expected=hmac.new(secret.encode(),str(timestamp).encode()+b"."+payload,hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected,value) for value in parts.get("v1",[]))

def _unix(value):
    if not value:return None
    from datetime import datetime,timezone
    return datetime.fromtimestamp(int(value),tz=timezone.utc)

async def _account_id_for_customer(con,customer,metadata):
    account_id=(metadata or {}).get("oriom7_account_id")
    if account_id:return account_id
    if customer:return await con.fetchval("SELECT account_id::text FROM oriom7_accounts WHERE stripe_customer_id=$1",customer)
    return None

def _plan_for_subscription(obj):
    metadata=obj.get("metadata") or {}
    plan=metadata.get("oriom7_plan_code")
    if plan in ("starter","builder","business","enterprise"):return plan
    for code,env_name in PLAN_PRICE_ENV.items():
        configured=os.getenv(env_name)
        items=((obj.get("items") or {}).get("data") or [])
        if configured and any(((item.get("price") or {}).get("id")==configured) for item in items):return code
    return "starter"

@router.post("/v1/billing/webhook")
async def stripe_webhook(request:Request):
    secret=os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:raise HTTPException(503,detail={"code":"webhook_not_configured"})
    payload=await request.body()
    if len(payload)>1_000_000:raise HTTPException(413,detail="Webhook payload too large.")
    signature=request.headers.get("stripe-signature","")
    if not _verify_signature(payload,signature,secret):
        raise HTTPException(400,detail={"code":"invalid_webhook_signature"})
    try:event=json.loads(payload)
    except (ValueError,UnicodeDecodeError):raise HTTPException(400,detail={"code":"invalid_webhook_payload"})
    event_id=event.get("id");event_type=event.get("type");obj=((event.get("data") or {}).get("object") or {})
    if not event_id or not event_type:raise HTTPException(400,detail={"code":"invalid_webhook_event"})
    pool=getattr(request.app.state,"database_pool",None)
    if pool is None:raise HTTPException(503,detail="Billing database is unavailable.")
    customer=obj.get("customer")
    metadata=obj.get("metadata") or {}
    safe_payload={"object_id":obj.get("id"),"customer":customer,"subscription":obj.get("subscription"),
                  "status":obj.get("status"),"metadata":{k:v for k,v in metadata.items() if k.startswith("oriom7_")}}
    async with pool.acquire() as con:
        async with con.transaction():
            inserted=await con.fetchval("""INSERT INTO oriom7_payment_events(provider,provider_event_id,event_type,payload)
             VALUES('stripe',$1,$2,$3::jsonb) ON CONFLICT(provider,provider_event_id) DO NOTHING RETURNING event_id""",
             event_id,event_type,json.dumps(safe_payload))
            if inserted is None:return {"received":True,"duplicate":True}
            account_id=await _account_id_for_customer(con,customer,metadata)
            if event_type=="checkout.session.completed":
                account_id=account_id or obj.get("client_reference_id")
                if account_id and customer:
                    await con.execute("UPDATE oriom7_accounts SET stripe_customer_id=$2,updated_at=NOW() WHERE account_id=$1::uuid",account_id,customer)
                subscription_id=obj.get("subscription")
                plan=(metadata.get("oriom7_plan_code") or "starter")
                organisation_id=metadata.get("oriom7_organisation_id")
                if account_id and subscription_id:
                    await con.execute("""INSERT INTO oriom7_subscriptions(account_id,organisation_id,plan_code,provider,provider_subscription_id,status)
                     VALUES($1::uuid,$2::uuid,$3,'stripe',$4,'pending')
                     ON CONFLICT(provider,provider_subscription_id) WHERE provider_subscription_id IS NOT NULL
                     DO UPDATE SET account_id=EXCLUDED.account_id,plan_code=EXCLUDED.plan_code,updated_at=NOW()""",
                     account_id,organisation_id,plan,subscription_id)
            elif event_type in ("customer.subscription.created","customer.subscription.updated","customer.subscription.deleted"):
                account_id=account_id or metadata.get("oriom7_account_id")
                subscription_id=obj.get("id")
                if account_id and subscription_id:
                    status=obj.get("status","incomplete")
                    if event_type.endswith(".deleted"):status="canceled"
                    if status not in ("pending","trialing","active","past_due","canceled","incomplete"):status="incomplete"
                    plan=_plan_for_subscription(obj)
                    organisation_id=metadata.get("oriom7_organisation_id")
                    period_start=_unix(obj.get("current_period_start"));period_end=_unix(obj.get("current_period_end"))
                    await con.execute("""INSERT INTO oriom7_subscriptions(account_id,organisation_id,plan_code,provider,provider_subscription_id,status,current_period_start,current_period_end)
                     VALUES($1::uuid,$2::uuid,$3,'stripe',$4,$5,$6,$7)
                     ON CONFLICT(provider,provider_subscription_id) WHERE provider_subscription_id IS NOT NULL
                     DO UPDATE SET account_id=EXCLUDED.account_id,plan_code=EXCLUDED.plan_code,status=EXCLUDED.status,
                       current_period_start=EXCLUDED.current_period_start,current_period_end=EXCLUDED.current_period_end,updated_at=NOW()""",
                     account_id,organisation_id,plan,subscription_id,status,period_start,period_end)
            elif event_type in ("invoice.finalized","invoice.paid","invoice.payment_failed","invoice.voided"):
                account_id=account_id or await _account_id_for_customer(con,customer,{})
                invoice_id=obj.get("id")
                if account_id and invoice_id:
                    amount_due=int(obj.get("amount_due") or 0);amount_paid=int(obj.get("amount_paid") or 0)
                    status="paid" if event_type=="invoice.paid" or (amount_due>0 and amount_paid>=amount_due) else ("void" if event_type=="invoice.voided" else "open")
                    subscription_ref=obj.get("subscription") or (((obj.get("parent") or {}).get("subscription_details") or {}).get("subscription"))
                    sub_id=await con.fetchval("SELECT subscription_id FROM oriom7_subscriptions WHERE provider='stripe' AND provider_subscription_id=$1",subscription_ref) if subscription_ref else None
                    await con.execute("""INSERT INTO oriom7_invoices(account_id,subscription_id,provider,provider_invoice_id,invoice_number,currency,
                     amount_due_minor,amount_paid_minor,status,hosted_invoice_url,issued_at,due_at)
                     VALUES($1::uuid,$2,'stripe',$3,$4,$5,$6,$7,$8,$9,$10,$11)
                     ON CONFLICT(provider,provider_invoice_id) DO UPDATE SET amount_due_minor=EXCLUDED.amount_due_minor,
                     amount_paid_minor=EXCLUDED.amount_paid_minor,status=EXCLUDED.status,hosted_invoice_url=EXCLUDED.hosted_invoice_url""",
                     account_id,sub_id,invoice_id,obj.get("number"),(obj.get("currency") or "usd").upper(),amount_due,amount_paid,status,
                     obj.get("hosted_invoice_url"),_unix(obj.get("created")),_unix(obj.get("due_date")))
            await con.execute("UPDATE oriom7_payment_events SET processed_at=NOW() WHERE event_id=$1",inserted)
    return {"received":True,"processed":True}
