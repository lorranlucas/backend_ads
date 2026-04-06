import asyncio
import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import AsyncSessionLocal

async def check_db():
    async with AsyncSessionLocal() as db:
        accs = await db.execute(text("SELECT count(*) FROM ad_accounts"))
        camps = await db.execute(text("SELECT count(*) FROM ad_campaigns"))
        ins = await db.execute(text("SELECT count(*) FROM ad_insights"))
        
        with open("db_counts.txt", "w") as f:
            f.write(f"Ad Accounts: {accs.scalar()}\n")
            f.write(f"Ad Campaigns: {camps.scalar()}\n")
            f.write(f"Ad Insights: {ins.scalar()}\n")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_db())
