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

class MonthlySpendOut(BaseModel):
    total: Decimal
    currency: str = "₽"
    percent_change: Optional[float] = None

class MonthlyPoint(BaseModel):
    month: str
    total: Decimal

class SpendHistoryOut(BaseModel):
    history: List[MonthlyPoint]

class CategoryItem(BaseModel):
    name: str
    amount: Decimal
    percentage: float
    color: str

class TopSubscriptionItem(BaseModel):
    name: str
    amount: Decimal
    period: str = "мес"
    icon_letter: str

class CategoriesOut(BaseModel):
    categories: List[CategoryItem]
    top_subscriptions: List[TopSubscriptionItem]
