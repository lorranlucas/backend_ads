from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.api.deps import get_current_user, get_db, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant
from app.models.ad_account import AdAccount
from app.models.ad_data import AdCampaign, AdInsight
from .filters import DashboardFilterParams

router = APIRouter()

@router.get("/kpis")
async def get_dashboard_kpis(
    filter_params: DashboardFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    query = select(
        func.sum(AdInsight.spend).label("spend"),
        func.sum(AdInsight.conversions).label("conversions"),
        func.sum(AdInsight.clicks).label("clicks"),
        func.sum(AdInsight.impressions).label("impressions")
    ).outerjoin(AdAccount, AdInsight.ad_account_id == AdAccount.id)\
     .filter(AdInsight.tenant_id == tenant.id)

    query = filter_params.apply_to_query(query, AdAccount, AdInsight)

    result = await db.execute(query)
    row = result.fetchone()
    
    spend = float(row.spend or 0)
    conversions = int(row.conversions or 0)
    clicks = int(row.clicks or 0)
    impressions = int(row.impressions or 0)
    
    revenue = spend * 4.0 # Mocking revenue multiplier for now if not in API
    roas = 4.0 if spend > 0 else 0
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    cpc = (spend / clicks) if clicks > 0 else 0
    cpm = (spend / impressions * 1000) if impressions > 0 else 0
    cpa = (spend / conversions) if conversions > 0 else 0
    
    return {
        "totalSpend": round(spend, 2),
        "totalRevenue": round(revenue, 2),
        "roas": round(roas, 2),
        "totalConversions": conversions,
        "ctr": round(ctr, 2),
        "cpc": round(cpc, 2),
        "cpm": round(cpm, 2),
        "cpa": round(cpa, 2),
        "leads": int(conversions * 0.4), # Mocking leads as fraction of conversions
        "costPerLead": round(spend / (conversions * 0.4), 2) if conversions > 0 else 0,
        "conversionRate": round((conversions / clicks * 100), 2) if clicks > 0 else 0,
        "frequency": 1.5,
        "impressions": impressions,
        "reach": int(impressions * 0.8)
    }

@router.get("/campaigns")
async def get_dashboard_campaigns(
    filter_params: DashboardFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    # Query real campaigns and aggregate their insights
    query = select(
        AdCampaign.id,
        AdCampaign.name,
        AdAccount.platform,
        func.sum(AdInsight.spend).label("spend"),
        func.sum(AdInsight.conversions).label("conversions"),
        func.sum(AdInsight.clicks).label("clicks"),
        func.sum(AdInsight.impressions).label("impressions")
    ).join(AdAccount, AdCampaign.ad_account_id == AdAccount.id) \
     .outerjoin(AdInsight, AdCampaign.id == AdInsight.campaign_id) \
     .filter(AdCampaign.tenant_id == tenant.id)
    
    query = filter_params.apply_to_query(query, AdAccount, AdInsight, AdCampaign)
    query = query.group_by(AdCampaign.id, AdCampaign.name, AdAccount.platform)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "status": "Ativo",
            "platform": r.platform.capitalize(),
            "spend": float(r.spend or 0),
            "revenue": float(r.spend or 0) * 4.0,
            "roas": 4.0 if r.spend else 0,
            "conversions": int(r.conversions or 0),
            "ctr": round((r.clicks / r.impressions * 100), 2) if r.impressions else 0,
            "cpc": round((r.spend / r.clicks), 2) if r.clicks else 0
        } for r in rows
    ]

@router.get("/funnel")
async def get_funnel_data(current_user: User = Depends(get_current_user)):
    return [
        {"step": "Impressões", "value": 3931481, "percentage": 100},
        {"step": "Cliques", "value": 58972, "percentage": 1.5},
        {"step": "Leads", "value": 450, "percentage": 0.76},
        {"step": "Vendas", "value": 185, "percentage": 41.1}
    ]
