import httpx
import os
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ad_account import AdAccount
from app.models.ad_data import AdCampaign, AdInsight
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_VERSION = "v18.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

class MetaService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_ad_accounts(self):
        """Fetch list of ad accounts the user has access to."""
        url = f"{BASE_URL}/me/adaccounts"
        params = {
            "fields": "name,account_id,id,currency",
            "access_token": self.access_token
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    async def sync_account_data(self, db: AsyncSession, ad_account: AdAccount, days: int = 90):
        """Main sync logic: campaigns and 90 days of insights."""
        external_id = ad_account.external_account_id
        if not external_id.startswith("act_"):
            external_id = f"act_{external_id}"

        # 1. Sync Campaigns
        campaigns = await self._fetch_campaigns(external_id)
        for camp_data in campaigns:
            camp_id = camp_data["id"]
            # Upsert Campaign
            result = await db.execute(select(AdCampaign).filter(AdCampaign.id == camp_id))
            campaign = result.scalars().first()
            
            if not campaign:
                campaign = AdCampaign(
                    id=camp_id,
                    tenant_id=ad_account.tenant_id,
                    ad_account_id=ad_account.id,
                    platform="meta"
                )
                db.add(campaign)
            
            campaign.name = camp_data["name"]
            campaign.status = camp_data["status"]
        
        await db.commit()

        # 2. Sync Daily Insights (last 90 days)
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        insights = await self._fetch_insights(external_id, start_date, end_date)
        
        for ins in insights:
            insight_date = datetime.strptime(ins["date_start"], "%Y-%m-%d").date()
            
            # Upsert Daily Insight
            result = await db.execute(
                select(AdInsight).filter(
                    AdInsight.ad_account_id == ad_account.id,
                    AdInsight.date == insight_date,
                    AdInsight.campaign_id == ins.get("campaign_id") # Can be null for account-level
                )
            )
            insight = result.scalars().first()
            
            if not insight:
                insight = AdInsight(
                    date=insight_date,
                    ad_account_id=ad_account.id,
                    tenant_id=ad_account.tenant_id,
                    campaign_id=ins.get("campaign_id")
                )
                db.add(insight)
            
            # Conversion check
            actions = ins.get("actions", [])
            conversions = sum(int(a["value"]) for a in actions if a["action_type"] in ["purchase", "lead", "offsite_conversion"])

            insight.spend = float(ins.get("spend", 0))
            insight.impressions = int(ins.get("impressions", 0))
            insight.clicks = int(ins.get("clicks", 0))
            insight.conversions = conversions

        await db.commit()
        return True

    async def _fetch_campaigns(self, ad_account_id: str):
        url = f"{BASE_URL}/{ad_account_id}/campaigns"
        params = {
            "fields": "name,status,id",
            "limit": 500,
            "access_token": self.access_token
        }
        res = await self.client.get(url, params=params)
        res.raise_for_status()
        return res.json().get("data", [])

    async def _fetch_insights(self, ad_account_id: str, start: str, end: str):
        url = f"{BASE_URL}/{ad_account_id}/insights"
        params = {
            "level": "campaign", 
            "time_range": f'{{"since":"{start}","until":"{end}"}}',
            "time_increment": 1,
            "fields": "campaign_id,spend,impressions,clicks,actions,date_start,date_stop",
            "limit": 500,
            "access_token": self.access_token
        }
        res = await self.client.get(url, params=params)
        res.raise_for_status()
        return res.json().get("data", [])
