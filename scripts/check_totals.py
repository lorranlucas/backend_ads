import asyncio
import os
from app.services.meta import MetaService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.ad_account import AdAccount
from sqlalchemy.future import select
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/dashboard_ads")

async def check_account_totals():
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AdAccount).filter(AdAccount.account_name.ilike("%Copinos%")))
        account = result.scalars().first()
        
        if not account:
            print("Conta não encontrada")
            return

        print(f"Checking Account Totals for: {account.account_name}")
        credentials = account.credentials
        token = credentials.get("access_token")
        
        async with MetaService(token) as service:
            external_id = account.external_account_id
            if not external_id.startswith("act_"):
                external_id = f"act_{external_id}"
            
            # Fetch Account Level Insights for the last 7 days
            url = f"https://graph.facebook.com/v18.0/{external_id}/insights"
            params = {
                "level": "account",
                "time_range": '{"since":"2026-04-01","until":"2026-04-07"}',
                "fields": "spend,impressions,clicks,actions,action_values,reach,frequency",
                "access_token": token
            }
            
            import httpx
            async with httpx.AsyncClient() as client:
                res = await client.get(url, params=params)
                data = res.json().get("data", [])
                if data:
                    ins = data[0]
                    print(f"ACCOUNT TOTALS (01/04 - 07/04):")
                    print(f"  Spend: {ins.get('spend')}")
                    print(f"  Impressions: {ins.get('impressions')}")
                    print(f"  Reach: {ins.get('reach')}")
                    print(f"  Actions: {ins.get('actions')}")
                    print(f"  Action Values: {ins.get('action_values')}")
                else:
                    print("No data found for this period at account level.")
                    print(res.json())

if __name__ == "__main__":
    asyncio.run(check_account_totals())
