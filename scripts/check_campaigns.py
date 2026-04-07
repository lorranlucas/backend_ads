import asyncio
import os
import httpx
from app.models.ad_account import AdAccount
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def run():
    engine = create_async_engine(DATABASE_URL)
    async with AsyncSession(engine) as db:
        res = await db.execute(select(AdAccount).filter(AdAccount.account_name.ilike('%Copinos%')))
        acc = res.scalars().first()
        token = acc.credentials.get("access_token")
        url = f"https://graph.facebook.com/v18.0/act_{acc.external_account_id}/campaigns"
        params = {
            "fields": "name,objective,optimization_goal,buying_type",
            "access_token": token
        }
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params)
            for c in r.json().get("data", []):
                print(f"Name: {c.get('name')}, Objective: {c.get('objective')}, Goal: {c.get('optimization_goal')}")

if __name__ == "__main__":
    asyncio.run(run())
