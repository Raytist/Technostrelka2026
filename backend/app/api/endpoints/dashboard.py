from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from decimal import Decimal
from typing import List

from app.db.database import get_db
from app.models.user import Users
from app.models.subscription import Subscriptions
from app.models.parsed_receipt import ParsedReceipts
from app.api.deps import get_current_user
from app.schemas.dashboard import DashboardSummaryOut, ParsedReceiptOut

router = APIRouter()

@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    active_subs = db.query(Subscriptions).filter(
        Subscriptions.user_id == current_user.id,
        Subscriptions.status.in_(["active", "custom"])
    ).all()
    
    monthly_total = sum((sub.amount for sub in active_subs if sub.amount), Decimal(0))
    
    unverified_count = db.query(Subscriptions).filter(
        Subscriptions.user_id == current_user.id,
        Subscriptions.status == "unverified"
    ).count()

    return DashboardSummaryOut(
        monthly_total=monthly_total,
        active_subscriptions_count=len(active_subs),
        unverified_count=unverified_count
    )

@router.get("/feed", response_model=List[ParsedReceiptOut])
def get_dashboard_feed(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    known_merchants = db.query(Subscriptions.raw_merchant_name).filter(
        Subscriptions.user_id == current_user.id
    ).all()
    known_merchants_list = [m[0].lower() for m in known_merchants if m[0]]

    feed_items = []
    receipts = db.query(ParsedReceipts).filter(
        ParsedReceipts.user_id == current_user.id
    ).order_by(ParsedReceipts.receipt_date.desc()).limit(50).all()
    
    seen_merchants = set()
    for r in receipts:
        if not r.merchant_name:
            continue
        m_lower = r.merchant_name.lower()
        if m_lower not in known_merchants_list and m_lower not in seen_merchants:
            if 0.5 <= r.amount <= 15 or r.amount % 10 == 9 or r.amount % 10 == 0:
                feed_items.append(r)
                seen_merchants.add(m_lower)
            
    return feed_items
