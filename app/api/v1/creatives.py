from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()

@router.get("/")
async def get_creatives(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return [
        {
            "id": "c1",
            "name": "Creative Video Black Friday",
            "format": "video",
            "spend": 5400,
            "clicks": 1200,
            "ctr": 1.8,
            "roas": 6.5,
            "image": "https://images.unsplash.com/photo-1611162147731-b3b063854199?w=400&q=80"
        },
        {
            "id": "c2",
            "name": "Static Banner Protein",
            "format": "image",
            "spend": 3200,
            "clicks": 850,
            "ctr": 1.2,
            "roas": 4.8,
            "image": "https://images.unsplash.com/photo-1593033509172-1300fce99041?w=400&q=80"
        }
    ]

@router.get("/summary")
async def get_creatives_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {
        "totalAnalyzed": 45,
        "topPerformer": "Creative Video Black Friday",
        "averageRoas": 4.2
    }
