from sqlalchemy import Column, String, ForeignKey, JSON
from app.database import Base
from app.models.base import TimeStampedModel
from sqlalchemy.orm import relationship

class AdAccount(Base, TimeStampedModel):
    __tablename__ = "ad_accounts"

    platform = Column(String, nullable=False, index=True)  # "meta" or "google"
    external_account_id = Column(String, nullable=False, unique=True, index=True)
    account_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    credentials = Column(JSON, nullable=True)  # Store encrypted tokens, etc.
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="ad_accounts")
    campaigns = relationship("AdCampaign", back_populates="ad_account", cascade="all, delete-orphan")
    insights = relationship("AdInsight", back_populates="ad_account", cascade="all, delete-orphan")
