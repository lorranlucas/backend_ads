from sqlalchemy import Column, String, Float, Integer, Date, ForeignKey, JSON
from app.database import Base
from app.models.base import TimeStampedModel
from sqlalchemy.orm import relationship

class AdCampaign(Base, TimeStampedModel):
    __tablename__ = "ad_campaigns"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    platform = Column(String, nullable=False)  # "meta" or "google"
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)

    # Relationships
    ad_account = relationship("AdAccount", back_populates="campaigns")
    insights = relationship("AdInsight", back_populates="campaign", cascade="all, delete-orphan")

class AdInsight(Base, TimeStampedModel):
    __tablename__ = "ad_insights"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    spend = Column(Float, default=0.0)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    link_clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    messages = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    leads = Column(Integer, default=0)
    checkouts_initiated = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    frequency = Column(Float, default=1.0)
    
    # Optional metadata for hierarchical view
    campaign_id = Column(String, ForeignKey("ad_campaigns.id"), nullable=True)
    adset_id = Column(String, nullable=True)
    adset_name = Column(String, nullable=True)
    ad_id = Column(String, nullable=True)
    ad_name = Column(String, nullable=True)
    
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)

    # Relationships
    campaign = relationship("AdCampaign", back_populates="insights")
    ad_account = relationship("AdAccount", back_populates="insights")
