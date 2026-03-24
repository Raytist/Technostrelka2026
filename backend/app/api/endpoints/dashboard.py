from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from decimal import Decimal
from typing import List
from datetime import datetime, timedelta
import calendar

from app.db.database import get_db
from app.models.user import Users
from app.models.subscription import Subscriptions
from app.models.parsed_receipt import ParsedReceipts
from app.api.deps import get_current_user
from app.schemas.dashboard import (
    DashboardSummaryOut, 
    ParsedReceiptOut, 
    MonthlySpendOut, 
    SpendHistoryOut, 
    MonthlyPoint, 
    CategoriesOut, 
    CategoryItem, 
    TopSubscriptionItem
)

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
            # Simple heuristic for trials
            if 0.5 <= r.amount <= 15 or r.amount % 10 == 9 or r.amount % 10 == 0:
                feed_items.append(r)
                seen_merchants.add(m_lower)
            
    return feed_items

@router.get("/analytics/monthly", response_model=MonthlySpendOut)
def get_monthly_analytics(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    now = datetime.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Current month predicted spend (active subs)
    active_subs = db.query(Subscriptions).filter(
        Subscriptions.user_id == current_user.id,
        Subscriptions.status.in_(["active", "custom"])
    ).all()
    current_total = sum((sub.amount for sub in active_subs if sub.amount), Decimal(0))

    # Previous month actual spend (receipts)
    prev_total = db.query(func.sum(ParsedReceipts.amount)).filter(
        ParsedReceipts.user_id == current_user.id,
        ParsedReceipts.receipt_date >= first_day_prev_month,
        ParsedReceipts.receipt_date <= last_day_prev_month
    ).scalar() or Decimal(0)

    percent_change = None
    if prev_total > 0:
        percent_change = float(((current_total - prev_total) / prev_total) * 100)

    return MonthlySpendOut(
        total=current_total,
        percent_change=percent_change
    )

@router.get("/analytics/history", response_model=SpendHistoryOut)
def get_spend_history(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    history = []
    now = datetime.now()
    
    # Russian month names for the chart
    months_ru = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i * 30) # Rough estimate for 6 months
        month_idx = target_date.month - 1
        year = target_date.year
        
        first_day = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        _, last_day_num = calendar.monthrange(year, month_idx + 1)
        last_day = target_date.replace(day=last_day_num, hour=23, minute=59, second=59)

        month_total = db.query(func.sum(ParsedReceipts.amount)).filter(
            ParsedReceipts.user_id == current_user.id,
            ParsedReceipts.receipt_date >= first_day,
            ParsedReceipts.receipt_date <= last_day
        ).scalar() or Decimal(0)

        history.append(MonthlyPoint(
            month=months_ru[month_idx],
            total=month_total
        ))

    return SpendHistoryOut(history=history)

@router.get("/analytics/categories", response_model=CategoriesOut)
def get_categories_analytics(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    active_subs = db.query(Subscriptions).filter(
        Subscriptions.user_id == current_user.id,
        Subscriptions.status.in_(["active", "custom"])
    ).all()

    categories_map = {
        "Кино и музыка": {"amount": Decimal(0), "color": "#A855F7"}, # Purple
        "Сервисы": {"amount": Decimal(0), "color": "#F97316"}, # Orange
        "Финансы": {"amount": Decimal(0), "color": "#EAB308"}, # Yellow
        "Другое": {"amount": Decimal(0), "color": "#94A3B8"}, # Slate
    }

    keywords = {
        "Кино и музыка": ["netflix", "кинопоиск", "spotify", "музыка", "apple music", "ivi", "okko", "youtube"],
        "Сервисы": ["яндекс плюс", "vk", "бусти", "telegram premium", "chatgpt", "cloud", "облако", "adobe"],
        "Финансы": ["тинькофф", "сбер", "банк", "insurance", "страховка"],
    }

    total_all = Decimal(0)
    for sub in active_subs:
        if not sub.amount: continue
        total_all += sub.amount
        name = (sub.name or sub.raw_merchant_name or "").lower()
        
        assigned = False
        for cat, kw_list in keywords.items():
            if any(kw in name for kw in kw_list):
                categories_map[cat]["amount"] += sub.amount
                assigned = True
                break
        
        if not assigned:
            categories_map["Другое"]["amount"] += sub.amount

    categories_list = []
    for name, data in categories_map.items():
        if total_all > 0:
            percentage = float((data["amount"] / total_all) * 100)
        else:
            percentage = 0
        
        categories_list.append(CategoryItem(
            name=name,
            amount=data["amount"],
            percentage=round(percentage, 1),
            color=data["color"]
        ))

    # Top 3 most expensive
    sorted_subs = sorted(active_subs, key=lambda x: x.amount or 0, reverse=True)[:3]
    top_items = []
    for s in sorted_subs:
        name = s.name or s.raw_merchant_name or "Unknown"
        top_items.append(TopSubscriptionItem(
            name=name,
            amount=s.amount or 0,
            icon_letter=name[0].upper() if name else "?"
        ))

    return CategoriesOut(
        categories=categories_list,
        top_subscriptions=top_items
    )
