from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class SubscriptionCreate(BaseModel):
    name: str
    amount: Decimal
    periodicity: str = "monthly"
    next_payment_date: datetime

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    periodicity: Optional[str] = None
    next_payment_date: Optional[datetime] = None
    status: Optional[str] = None

class SubscriptionOut(BaseModel):
    id: UUID
    raw_merchant_name: Optional[str]
    name: str
    amount: Decimal
    status: str
    periodicity: str
    next_payment_date: Optional[datetime]
    
    class Config:
        from_attributes = True
