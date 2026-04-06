from sqlalchemy import Column, DateTime, String, func
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class TimeStampedModel:
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
