from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.api.deps import get_current_user, get_db, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant
from app.models.ad_account import AdAccount
from app.models.ad_data import AdInsight
from app.schemas.ad_account import AdAccount as AdAccountSchema, AdAccountCreate
from app.services.meta import MetaService
import uuid
import os
from .filters import DashboardFilterParams

router = APIRouter()

async def run_sync(db: AsyncSession, ad_account: AdAccount):
    # Use the token specific to the tenant/account
    token = None
    if ad_account.credentials:
        token = ad_account.credentials.get("access_token")
        
    if not token: 
        print(f"No Meta Access Token found in database for account {ad_account.external_account_id}")
        return
        
    service = MetaService(token)
    async with service:
        try:
            await service.sync_account_data(db, ad_account, days=90)
            print(f"Sync completed for account {ad_account.external_account_id}")
        except Exception as e:
            print(f"Error syncing account {ad_account.external_account_id}: {e}")

@router.get("/accounts", response_model=list[AdAccountSchema])
async def get_agency_accounts(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    result = await db.execute(select(AdAccount).filter(AdAccount.tenant_id == tenant.id))
    return result.scalars().all()

@router.post("/accounts", response_model=AdAccountSchema)
async def create_agency_account(
    account_in: AdAccountCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    # Check if already exists
    result = await db.execute(
        select(AdAccount).filter(
            AdAccount.tenant_id == tenant.id,
            AdAccount.external_account_id == account_in.external_account_id
        )
    )
    ad_account = result.scalars().first()
    
    if not ad_account:
        ad_account = AdAccount(
            **account_in.model_dump(),
            id=str(uuid.uuid4()),
            tenant_id=tenant.id
        )
        db.add(ad_account)
        await db.commit()
        await db.refresh(ad_account)
    
    # Trigger Sync
    background_tasks.add_task(run_sync, db, ad_account)
    
    return ad_account

@router.delete("/accounts/{account_id}")
async def fetch_and_delete_agency_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    result = await db.execute(select(AdAccount).filter(AdAccount.id == account_id, AdAccount.tenant_id == tenant.id))
    ad_account = result.scalars().first()
    
    if not ad_account:
        raise HTTPException(status_code=404, detail="Ad account not found")
        
    await db.delete(ad_account)
    await db.commit()
    
    return {"status": "success", "message": "Account deleted successfully"}


@router.get("/kpis")
async def get_agency_kpis(
    filter_params: DashboardFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    # Query real insights from DB
    query = select(
        func.sum(AdInsight.spend).label("total_spend"),
        func.sum(AdInsight.clicks).label("total_clicks"),
        func.sum(AdInsight.impressions).label("total_impressions"),
        func.sum(AdInsight.conversions).label("total_conversions")
    ).outerjoin(AdAccount, AdInsight.ad_account_id == AdAccount.id)\
     .filter(AdInsight.tenant_id == tenant.id)
     
    query = filter_params.apply_to_query(query, AdAccount, AdInsight)
    
    result = await db.execute(query)
    row = result.fetchone()
    
    if not row or not row.total_spend:
        return [{
            "title": "Geral",
            "gastoNoPeriodo": 0, "gastoVariacao": 0, "cliquesNoLink": 0, "cliquesVariacao": 0,
            "ctrMedio": 0, "ctrVariacao": 0, "mensagens": 0, "mensagensVariacao": 0,
            "alcanceIG": 0, "alcanceVariacao": 0, "previsaoMes": 0
        }]
    
    ctr = (row.total_clicks / row.total_impressions * 100) if row.total_impressions else 0
    
    return [{
        "title": "Geral",
        "gastoNoPeriodo": round(row.total_spend, 2),
        "gastoVariacao": 0,
        "cliquesNoLink": row.total_clicks,
        "cliquesVariacao": 0,
        "ctrMedio": round(ctr, 2),
        "ctrVariacao": 0,
        "mensagens": row.total_conversions,
        "mensagensVariacao": 0,
        "alcanceIG": row.total_impressions,
        "alcanceVariacao": 0,
        "previsaoMes": round(row.total_spend * 1.2, 2)
    }]

@router.post("/sync")
async def trigger_manual_sync(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    result = await db.execute(select(AdAccount).filter(AdAccount.tenant_id == tenant.id))
    accounts = result.scalars().all()
    for acc in accounts:
        background_tasks.add_task(run_sync, db, acc)
    return {"status": "Sync tasks scheduled for all accounts"}

@router.get("/daily-data")
async def get_daily_data(
    days: int = 7,
    filter_params: DashboardFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    # Aggregate real daily data
    
    query = select(
        AdInsight.date,
        func.sum(AdInsight.spend).label("spend"),
        func.sum(AdInsight.conversions).label("conversions"),
        func.sum(AdInsight.clicks).label("clicks"),
        func.sum(AdInsight.impressions).label("impressions")
    ).outerjoin(AdAccount, AdInsight.ad_account_id == AdAccount.id)\
     .filter(AdInsight.tenant_id == tenant.id)
     
    query = filter_params.apply_to_query(query, AdAccount, AdInsight)
    
    query = query.group_by(AdInsight.date).order_by(AdInsight.date.desc()).limit(days)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    return {
        "current": [{
            "date": r.date.strftime("%d/%m"), 
            "totalSpend": r.spend or 0, 
            "totalConversions": r.conversions or 0,
            "ctr": round((r.clicks / r.impressions * 100), 2) if r.impressions else 0
        } for r in reversed(rows)],
        "previous": []
    }

@router.get("/investment-by-client")
async def get_investment_by_client(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {"name": "Growth Co", "investimento": 15000, "percen": 35},
        {"name": "SaaS Guru", "investimento": 12000, "percen": 28},
        {"name": "E-com Master", "investimento": 8000, "percen": 18}
    ]

@router.get("/top-clients-audience")
async def get_top_clients_audience(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {"name": "Growth Co", "audience": 45000, "engagement": 4.2},
        {"name": "SaaS Guru", "audience": 32000, "engagement": 3.8},
        {"name": "E-com Master", "audience": 28000, "engagement": 5.1}
    ]

@router.get("/instagram-clients")
async def get_instagram_clients(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {"id": "1", "name": "Growth Co", "account": "@growth_co", "followers": 12400, "growth": 5.2},
        {"id": "2", "name": "SaaS Guru", "account": "@saas_guru", "followers": 8500, "growth": 3.1},
    ]

@router.get("/meta-clients")
async def get_meta_clients(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    # Query real accounts and their aggregated metrics
    result = await db.execute(
        select(
            AdAccount.id,
            AdAccount.account_name.label("name"),
            func.sum(AdInsight.spend).label("spend"),
            func.sum(AdInsight.clicks).label("clicks"),
            func.sum(AdInsight.impressions).label("impressions")
        ).outerjoin(AdInsight, AdAccount.id == AdInsight.ad_account_id)
        .filter(AdAccount.tenant_id == tenant.id, AdAccount.platform == "meta")
        .group_by(AdAccount.id, AdAccount.account_name)
    )
    rows = result.fetchall()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "status": "active",
            "spend": float(r.spend or 0),
            "clicks": int(r.clicks or 0),
            "ctr": round((r.clicks / r.impressions * 100), 2) if r.impressions else 0,
            "color": f"hsl({(hash(r.id) % 360)}, 70%, 50%)" # Deterministic color
        } for r in rows
    ]
