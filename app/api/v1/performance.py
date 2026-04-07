from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.api.deps import get_db, get_current_tenant
from app.models.tenant import Tenant
from app.models.ad_account import AdAccount
from app.models.ad_data import AdCampaign, AdInsight
from .filters import DashboardFilterParams
from app.core.logging_route import TenantLoggingRoute
from typing import List, Dict, Any

router = APIRouter(route_class=TenantLoggingRoute)

@router.get("/performance-table")
async def get_performance_table(
    filter_params: DashboardFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    # Base query for all insights at the most granular level (Ad)
    # We aggregate by Campaign, AdSet, and Ad
    query = select(
        AdInsight.campaign_id,
        AdCampaign.name.label("campaign_name"),
        AdInsight.adset_id,
        AdInsight.adset_name,
        AdInsight.ad_id,
        AdInsight.ad_name,
        func.sum(AdInsight.spend).label("spend"),
        func.sum(AdInsight.impressions).label("impressions"),
        func.sum(AdInsight.reach).label("reach"),
        func.sum(AdInsight.clicks).label("clicks"),
        func.sum(AdInsight.link_clicks).label("link_clicks"),
        func.sum(AdInsight.conversions).label("conversions"),
        func.sum(AdInsight.messages).label("messages"),
        func.sum(AdInsight.purchases).label("purchases"),
        func.sum(AdInsight.leads).label("leads"),
        func.sum(AdInsight.checkouts_initiated).label("checkouts_initiated"),
        func.sum(AdInsight.revenue).label("revenue")
    ).join(AdCampaign, AdInsight.campaign_id == AdCampaign.id) \
     .join(AdAccount, AdCampaign.ad_account_id == AdAccount.id) \
     .filter(AdInsight.tenant_id == tenant.id)

    query = filter_params.apply_to_query(query, AdAccount, AdInsight, AdCampaign)
    
    query = query.group_by(
        AdInsight.campaign_id, 
        AdCampaign.name,
        AdInsight.adset_id, 
        AdInsight.adset_name, 
        AdInsight.ad_id, 
        AdInsight.ad_name
    )

    result = await db.execute(query)
    rows = result.fetchall()

    # Build the tree structure
    campaigns: Dict[str, Any] = {}

    for r in rows:
        c_id = r.campaign_id
        as_id = r.adset_id or "unknown_adset"
        a_id = r.ad_id or "unknown_ad"

        # Ensure campaign exists
        if c_id not in campaigns:
            campaigns[c_id] = {
                "id": c_id,
                "name": r.campaign_name,
                "type": "campaign",
                "spend": 0, "impressions": 0, "reach": 0, "clicks": 0, "conversions": 0, "revenue": 0,
                "adsets": {}
            }
        
        c = campaigns[c_id]
        
        # Ensure adset exists in campaign
        if as_id not in c["adsets"]:
            c["adsets"][as_id] = {
                "id": as_id,
                "name": r.adset_name or "Desconhecido",
                "type": "adset",
                "spend": 0, "impressions": 0, "reach": 0, "clicks": 0, "conversions": 0, "revenue": 0,
                "ads": []
            }
        
        as_data = c["adsets"][as_id]

        # Metric data for the leaf (Ad)
        metrics = {
            "spend": float(r.spend or 0),
            "impressions": int(r.impressions or 0),
            "reach": int(r.reach or 0),
            "clicks": int(r.clicks or 0),
            "link_clicks": int(r.link_clicks or 0),
            "conversions": int(r.conversions or 0),
            "messages": int(r.messages or 0),
            "purchases": int(r.purchases or 0),
            "leads": int(r.leads or 0),
            "checkouts_initiated": int(r.checkouts_initiated or 0),
            "revenue": float(r.revenue or 0)
        }
        
        # Add metrics to parent (AdSet)
        for key in metrics:
            as_data[key] += metrics[key]
            # Add metrics to root (Campaign)
            c[key] += metrics[key]

        # Add Ad to AdSet
        as_data["ads"].append({
            "id": a_id,
            "name": r.ad_name or "Anúncio sem nome",
            "type": "ad",
            **metrics
        })

    # Flatten and calculate KPIs
    def calculate_kpis(item):
        spend = item["spend"]
        rev = item["revenue"]
        clicks = item["clicks"]
        link_clicks = item["link_clicks"]
        impr = item["impressions"]
        conv = item["conversions"]
        
        item["roas"] = rev / spend if spend > 0 else 0
        item["ctr"] = (link_clicks / impr * 100) if impr > 0 else 0
        item["cpc"] = spend / link_clicks if link_clicks > 0 else 0
        item["cpm"] = (spend / impr * 1000) if impr > 0 else 0
        item["cpa"] = spend / conv if conv > 0 else 0
        item["status"] = "Ativo" # Fallback status
        
        if "adsets" in item:
            for as_item in item["adsets"]:
                calculate_kpis(as_item)
        if "ads" in item:
            for ad_item in item["ads"]:
                calculate_kpis(ad_item)

    final_tree = []
    for c_id, c_data in campaigns.items():
        # Convert adsets dict to list
        adsets_list = []
        for as_id, as_data in c_data["adsets"].items():
            adsets_list.append(as_data)
        
        c_data["adsets"] = adsets_list
        calculate_kpis(c_data)
        final_tree.append(c_data)

    return final_tree
