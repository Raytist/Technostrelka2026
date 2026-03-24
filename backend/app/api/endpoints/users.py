from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import Users
from app.api.deps import get_current_user
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserOut)
def get_user_profile(current_user: Users = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserOut)
def update_user_profile(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    if user_data.fcm_token is not None:
        current_user.fcm_token = user_data.fcm_token
    if user_data.push_enabled is not None:
        current_user.push_enabled = user_data.push_enabled
        
    db.commit()
    db.refresh(current_user)
    return current_user
