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
        
        # Cache existing campaign IDs for this account to avoid FK errors
        campaign_res = await db.execute(select(AdCampaign.id).filter(AdCampaign.ad_account_id == ad_account.id))
        existing_campaign_ids = set(campaign_res.scalars().all())
        
        for ins in insights:
            insight_date = datetime.strptime(ins["date_start"], "%Y-%m-%d").date()
            
            campaign_id = ins.get("campaign_id")
            
            # Ensure campaign_id exists in DB to avoid ForeignKeyViolationError
            if campaign_id and campaign_id not in existing_campaign_ids:
                # If the campaign doesn't exist, we'll store the insight without campaign_id 
                # or we could create a placeholder. Setting to None is safer for raw metrics.
                print(f"Aviso: Campanha {campaign_id} não encontrada no DB. Definindo como NULL para insight.")
                campaign_id = None
                
            adset_id = ins.get("adset_id")
            adset_name = ins.get("adset_name")
            ad_id = ins.get("ad_id")
            ad_name = ins.get("ad_name")
            
            # Upsert Daily Insight - Ad Level (ad_id + date + ad_account_id)
            query = select(AdInsight).filter(
                AdInsight.ad_account_id == ad_account.id,
                AdInsight.date == insight_date,
                AdInsight.ad_id == ad_id
            )
            
            result = await db.execute(query)
            insight = result.scalars().first()
            
            if not insight:
                insight = AdInsight(
                    date=insight_date,
                    ad_account_id=ad_account.id,
                    tenant_id=ad_account.tenant_id,
                    campaign_id=campaign_id,
                    adset_id=adset_id,
                    adset_name=adset_name,
                    ad_id=ad_id,
                    ad_name=ad_name
                )
                db.add(insight)
            else:
                # Update names in case they changed in Meta
                insight.campaign_id = campaign_id
                insight.adset_name = adset_name
                insight.ad_name = ad_name
                        # --- ROBUST METRIC EXTRACTION ---
            actions = ins.get("actions", [])
            action_values = ins.get("action_values", [])
            conv_map = {a["action_type"]: int(a["value"]) for a in actions}
            val_map = {v["action_type"]: float(v["value"]) for v in action_values}
            
            # 1. Revenue (Conversion Value)
            # Use specific conversion value fields to match Meta 'Account Value'
            revenue = (
                val_map.get("purchase", 0) + 
                val_map.get("onsite_purchase", 0) +
                val_map.get("offsite_conversion.fb_pixel_purchase", 0)
            )
            
            # 2. Specific Conversions
            purchases = conv_map.get("purchase", 0) or conv_map.get("offsite_conversion.fb_pixel_purchase", 0)
            leads = conv_map.get("lead", 0) or conv_map.get("offsite_conversion.fb_pixel_lead", 0)
            messages = conv_map.get("onsite_conversion.messaging_conversation_started_7d", 0)
            checkouts = conv_map.get("initiate_checkout", 0) or conv_map.get("offsite_conversion.fb_pixel_initiate_checkout", 0)
            
            # 3. Results (Standard Meta Results Logic)
            # We follow the optimization goal if possible, otherwise we show 'Purchases' as default results
            # For now, we take the sum of hard conversions as the 'results balance'
            conversions = purchases + leads + messages
            
            # 4. Traffic Metrics
            total_clicks = int(ins.get("clicks", 0))
            link_clicks = conv_map.get("link_click", 0)

            insight.spend = float(ins.get("spend", 0))
            insight.impressions = int(ins.get("impressions", 0))
            insight.clicks = total_clicks
            insight.link_clicks = link_clicks
            insight.conversions = conversions
            insight.purchases = purchases
            insight.leads = leads
            insight.messages = messages
            insight.checkouts_initiated = checkouts
            insight.reach = int(ins.get("reach", 0))
            insight.frequency = float(ins.get("frequency", 1.0))
            insight.revenue = revenue


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
            "level": "ad", 
            "time_range": f'{{"since":"{start}","until":"{end}"}}',
            "time_increment": 1,
            "fields": "campaign_id,adset_id,adset_name,ad_id,ad_name,spend,impressions,clicks,actions,action_values,reach,frequency,date_start,date_stop,optimization_goal",
            "limit": 500,
            "access_token": self.access_token
        }
        res = await self.client.get(url, params=params)
        res.raise_for_status()
        return res.json().get("data", [])
