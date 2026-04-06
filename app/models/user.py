from sqlalchemy import Column, String, Boolean, ForeignKey, Enum
import enum
from app.database import Base
from app.models.base import TimeStampedModel
from sqlalchemy.orm import relationship

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class User(Base, TimeStampedModel):
    __tablename__ = "users"

    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    role = Column(String, default=UserRole.VIEWER)
