import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base

class Subscriptions(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    raw_merchant_name = Column(String, index=True)
    name = Column(String)
    amount = Column(Numeric(12, 2))
    status = Column(String, default="unverified") # active, unverified, rejected, canceled, trial, custom
    periodicity = Column(String, default="monthly")
    next_payment_date = Column(DateTime(timezone=True))
