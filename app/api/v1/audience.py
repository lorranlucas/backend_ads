from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.core.logging_route import TenantLoggingRoute

router = APIRouter(route_class=TenantLoggingRoute)

@router.get("/demographics")
async def get_audience_demographics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {"faixa": "18-24", "masculino": 12, "feminino": 15},
        {"faixa": "25-34", "masculino": 25, "feminino": 28},
        {"faixa": "35-44", "masculino": 18, "feminino": 16},
        {"faixa": "45-54", "masculino": 8, "feminino": 10},
    ]

@router.get("/locations")
async def get_audience_locations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {"estado": "SP", "valor": 4500, "porcentagem": 35},
        {"estado": "RJ", "valor": 2800, "porcentagem": 22},
        {"estado": "MG", "valor": 1500, "porcentagem": 12},
    ]

@router.get("/engagement")
async def get_audience_engagement(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {"step": "Curtidas", "value": 12450},
        {"step": "Comentários", "value": 1200},
        {"step": "Compartilhamentos", "value": 450},
        {"step": "Salvamentos", "value": 890},
    ]

@router.get("/profile-clicks")
async def get_client_profile_clicks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {"date": "01/04", "clicks": 120},
        {"date": "02/04", "clicks": 145},
        {"date": "03/04", "clicks": 132},
        {"date": "04/04", "clicks": 168},
        {"date": "05/04", "clicks": 154},
        {"date": "06/04", "clicks": 190},
        {"date": "07/04", "clicks": 175}
    ]
