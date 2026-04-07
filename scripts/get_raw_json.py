import asyncio
import json
import os
from datetime import datetime, timedelta
from app.services.meta import MetaService
from dotenv import load_dotenv

load_dotenv()

async def main():
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        print("Erro: META_ACCESS_TOKEN não encontrado no .env")
        return

    async with MetaService(token) as meta:
        # User is interested in 'C138' which matches 'C.A oficial 138'
        target_account = "act_1480354320343383"
        
        print(f"\nBuscando dados brutos para: {target_account} (C.A oficial 138)")
        
        # 17/03 was mentioned in first message, let's look around that or just last 30 days
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            raw_insights = await meta._fetch_insights(target_account, start_date, end_date)
            print("\n--- JSON BRUTO DO META (Últimos 30 dias) ---")
            if not raw_insights:
                print("Nenhum dado encontrado para este período.")
            else:
                # Show only first 5 records to avoid hitting output limits
                print(json.dumps(raw_insights[:5], indent=2))
                print(f"\n... (Total de {len(raw_insights)} registros encontrados)")
            print("--- FIM DO JSON ---")
        except Exception as e:
            print(f"Erro ao buscar insights: {e}")

if __name__ == "__main__":
    asyncio.run(main())
