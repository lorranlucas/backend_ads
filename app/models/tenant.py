from sqlalchemy import Column, String, Boolean
from app.database import Base
from app.models.base import TimeStampedModel
from sqlalchemy.orm import relationship

class Tenant(Base, TimeStampedModel):
    __tablename__ = "tenants"

    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    users = relationship("User", back_populates="tenant")
    ad_accounts = relationship("AdAccount", back_populates="tenant")
