import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base

class ParsedReceipts(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    message_id = Column(String, unique=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    merchant_name = Column(String, index=True)
    receipt_date = Column(DateTime(timezone=True), nullable=False)
    is_trial = Column(Boolean, default=False)
