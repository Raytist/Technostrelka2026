from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserUpdate(BaseModel):
    fcm_token: Optional[str] = None
    push_enabled: Optional[bool] = None

class UserOut(BaseModel):
    id: UUID
    fcm_token: Optional[str]
    push_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
