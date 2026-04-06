from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class AdAccountBase(BaseModel):
    platform: str  # "meta" or "google"
    external_account_id: str
    account_name: str
    status: str = "active"
    credentials: Optional[Dict[str, Any]] = None

class AdAccountCreate(AdAccountBase):
    pass

class AdAccount(AdAccountBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConnectionStatus(BaseModel):
    has_connections: bool
    count: int
