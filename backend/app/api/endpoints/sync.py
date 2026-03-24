from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import get_db
from app.models.user import Users
from app.api.deps import get_current_user
from app.workers.tasks import mail_fetch_task

router = APIRouter()

@router.post("/start")
def start_sync(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """
    Triggers the Celery task to fetch emails for this user immediately.
    """
    mail_fetch_task.delay(str(current_user.id))
    return {"status": "Sync queued successfully for user."}
