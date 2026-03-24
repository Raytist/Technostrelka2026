from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class DashboardSummaryOut(BaseModel):
    monthly_total: Decimal
    active_subscriptions_count: int
    unverified_count: int

class ParsedReceiptOut(BaseModel):
    id: UUID
    merchant_name: str
    amount: Decimal
    receipt_date: datetime
    
    class Config:
        from_attributes = True
