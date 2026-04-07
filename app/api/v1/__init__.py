from fastapi import APIRouter
from app.api.v1 import (
    dashboard,
    agency,
    audience,
    creatives,
    auth,
    performance
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(agency.router, prefix="/agency", tags=["agency"])
api_router.include_router(audience.router, prefix="/audience", tags=["audience"])
api_router.include_router(creatives.router, prefix="/creatives", tags=["creatives"])
api_router.include_router(performance.router, prefix="/dashboard", tags=["performance"])
