import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base_class import Base

class Users(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fcm_token = Column(String, nullable=True)
    push_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
