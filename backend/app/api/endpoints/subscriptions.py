from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from dateutil.relativedelta import relativedelta

from app.db.database import get_db
from app.models.user import Users
from app.models.subscription import Subscriptions
from app.api.deps import get_current_user
from app.schemas.subscription import SubscriptionOut, SubscriptionUpdate, SubscriptionCreate

router = APIRouter()

@router.get("", response_model=List[SubscriptionOut])
def list_subscriptions(
    status: Optional[str] = Query(None, description="Filter by status (e.g. active, unverified, rejected)"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    query = db.query(Subscriptions).filter(Subscriptions.user_id == current_user.id)
    if status and status.lower() != "all":
        query = query.filter(Subscriptions.status == status)
    return query.all()

@router.post("", response_model=SubscriptionOut)
def manual_create_subscription(
    sub_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    new_sub = Subscriptions(
        user_id=current_user.id,
        raw_merchant_name=sub_data.name.upper(),
        name=sub_data.name,
        amount=sub_data.amount,
        status="custom",
        periodicity=sub_data.periodicity,
        next_payment_date=sub_data.next_payment_date
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub

@router.patch("/{sub_id}/verify", response_model=SubscriptionOut)
def verify_subscription(
    sub_id: UUID, 
    db: Session = Depends(get_db), 
    current_user: Users = Depends(get_current_user)
):
    sub = db.query(Subscriptions).filter(Subscriptions.id == sub_id, Subscriptions.user_id == current_user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    if sub.status == "unverified":
        sub.status = "active"
        if not sub.next_payment_date:
            sub.next_payment_date = datetime.utcnow() + relativedelta(months=1)
        db.commit()
        db.refresh(sub)
    return sub

@router.patch("/{sub_id}/reject", response_model=SubscriptionOut)
def reject_subscription(
    sub_id: UUID, 
    db: Session = Depends(get_db), 
    current_user: Users = Depends(get_current_user)
):
    sub = db.query(Subscriptions).filter(Subscriptions.id == sub_id, Subscriptions.user_id == current_user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    sub.status = "rejected"
    db.commit()
    db.refresh(sub)
    return sub
    
@router.patch("/{sub_id}", response_model=SubscriptionOut)
def update_subscription(
    sub_id: UUID, 
    data: SubscriptionUpdate,
    db: Session = Depends(get_db), 
    current_user: Users = Depends(get_current_user)
):
    sub = db.query(Subscriptions).filter(Subscriptions.id == sub_id, Subscriptions.user_id == current_user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    if data.name is not None:
        sub.name = data.name
    if data.periodicity is not None:
        sub.periodicity = data.periodicity
    if data.next_payment_date is not None:
        sub.next_payment_date = data.next_payment_date
        
    db.commit()
    db.refresh(sub)
    return sub
