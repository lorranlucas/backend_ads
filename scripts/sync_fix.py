import asyncio
import os
import sys
from datetime import datetime

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal, engine
from app.models.ad_account import AdAccount
from app.services.meta import MetaService
from sqlalchemy.future import select

async def repair_account(account_name_like: str, days: int = 90):
    async with AsyncSessionLocal() as db:
        print(f"Buscando conta: {account_name_like} (Sincronizando {days} dias)...")
        result = await db.execute(
            select(AdAccount).filter(AdAccount.account_name.ilike(f"%{account_name_like}%"))
        )
        account = result.scalars().first()
        
        if not account:
            print(f"ERRO: Conta '{account_name_like}' não encontrada.")
            return

        print(f"Encontrada: {account.account_name} ({account.external_account_id})")
        
        # Get token from credentials or env
        token = None
        if account.credentials:
            token = account.credentials.get("access_token")
        
        if not token:
            token = os.getenv("META_ACCESS_TOKEN")
            print("Usando token global do .env")
        else:
            print("Usando token específico da conta")

        if not token:
            print("ERRO: Nenhum token de acesso encontrado.")
            return

        try:
            service = MetaService(token)
            async with service:
                print(f"Iniciando sincronização para {account.account_name}...")
                await service.sync_account_data(db, account, days=days)
                print("Sincronização concluída!")

            # Verificar se dados foram persistidos
            from app.models.ad_data import AdInsight
            from sqlalchemy import func
            
            res = await db.execute(
                select(func.sum(AdInsight.spend), func.min(AdInsight.date), func.max(AdInsight.date)).filter(AdInsight.ad_account_id == account.id)
            )
            row = res.fetchone()
            total_spend = row[0] or 0
            min_date = row[1]
            max_date = row[2]
            print(f"Gasto Total no DB agora: R$ {total_spend:.2f}")
            print(f"Período no DB: {min_date} até {max_date}")
        except Exception as e:
            import traceback
            print(f"ERRO durante a sincronização: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Copinos", help="Nome da conta ou parte dele")
    parser.add_argument("--days", type=int, default=90, help="Quantidade de dias para sincronizar")
    args = parser.parse_args()
    
    asyncio.run(repair_account(args.name, args.days))
