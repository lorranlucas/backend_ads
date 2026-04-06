import asyncio
import os
import sys

# Add the app directory to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.ad_data import AdCampaign, AdInsight
from app.models.ad_account import AdAccount

async def test_campaign_query():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                AdCampaign.id,
                AdCampaign.name,
                AdAccount.platform,
                func.sum(AdInsight.spend).label("spend"),
            ).join(AdAccount, AdCampaign.ad_account_id == AdAccount.id)
            .outerjoin(AdInsight, AdCampaign.id == AdInsight.campaign_id)
            .group_by(AdCampaign.id, AdCampaign.name, AdAccount.platform)
        )
        rows = result.fetchall()
        print(f"Total campaigns matching logic: {len(rows)}")
        for r in rows:
            print(f"- {r.name}: {r.spend}")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_campaign_query())
