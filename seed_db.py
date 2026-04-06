import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import engine, AsyncSessionLocal, Base
from app.models import Tenant, User, UserRole, AdAccount, AdCampaign, AdInsight
from app.core.security import get_password_hash
import uuid

async def seed():
    # Create tables if they don't exist
    print("Ensuring tables are created...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if tenant already exists
            result = await db.execute(select(Tenant))
            if result.scalars().first():
                print("Database already has data. Skipping seed.")
                return

            print("Seeding database...")
            
            # Create Default Tenant
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Agência Principal",
                slug="agencia-principal"
            )
            db.add(tenant)
            await db.flush() # Get tenant ID
            
            # Create Admin User
            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin@agencia.com",
                full_name="Administrador do Sistema",
                hashed_password=get_password_hash("admin123"),
                tenant_id=tenant.id,
                role=UserRole.ADMIN
            )
            db.add(admin_user)
            
            # Create Demo User
            demo_user = User(
                id=str(uuid.uuid4()),
                email="demo@agencia.com",
                full_name="Usuário Demo",
                hashed_password=get_password_hash("demo123"),
                tenant_id=tenant.id,
                role=UserRole.VIEWER
            )
            db.add(demo_user)
            
            await db.commit()
            print("Seed completed successfully!")
        except Exception as e:
            import traceback
            print(f"Error seeding database: {e}")
            traceback.print_exc()
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(seed())
