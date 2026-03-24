from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.user import Users
from app.models.yandex_connection import YandexConnections
from app.core.security import create_access_token, encrypt_token
from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter()

@router.get("/yandex")
def yandex_login():
    """Redirects to Yandex OAuth authorization page."""
    if not settings.YANDEX_CLIENT_ID:
        raise HTTPException(
            status_code=500, 
            detail="Yandex Client ID is not configured in .env"
        )
    redirect_url = f"https://oauth.yandex.ru/authorize?response_type=code&client_id={settings.YANDEX_CLIENT_ID}"
    return RedirectResponse(redirect_url)

@router.get("/yandex/callback")
async def yandex_callback(code: str = None, db: Session = Depends(get_db)):
    """Handles Yandex callback, fetches tokens, and creates internal User/JWT."""
    if not code:
        raise HTTPException(
            status_code=400, 
            detail="Authorization code is missing. Please start from /api/v1/auth/yandex"
        )
    
    token_url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.YANDEX_CLIENT_ID,
        "client_secret": settings.YANDEX_CLIENT_SECRET
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            error_data = response.json() if response.status_code < 500 else {"error": "Internal Yandex Error"}
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to get token from Yandex: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
            )
            
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        
        # Get user info (email)
        user_info_resp = await client.get(
            "https://login.yandex.ru/info", 
            headers={"Authorization": f"OAuth {access_token}"}
        )
        if user_info_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Yandex")
            
        user_info = user_info_resp.json()
        email = user_info.get("default_email")
        
        # If the Yandex API app settings don't have "Access to email address" enabled,
        # fallback to using the login username + @yandex.ru
        if not email and user_info.get("login"):
            email = f"{user_info.get('login')}@yandex.ru"
            
        if not email:
            raise HTTPException(status_code=400, detail="Could not determine Yandex email.")

        # Find or create user connection
        connection = db.query(YandexConnections).filter(YandexConnections.email == email).first()
        
        if not connection:
            # Create a new user
            user = Users()
            db.add(user)
            db.flush() # get user.id
            
            connection = YandexConnections(
                user_id=user.id,
                email=email,
                access_token=encrypt_token(access_token),
                refresh_token=encrypt_token(refresh_token),
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
            )
            db.add(connection)
        else:
            # Update tokens
            connection.access_token = encrypt_token(access_token)
            connection.refresh_token = encrypt_token(refresh_token)
            connection.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
        db.commit()
        
        # Generate our own internal JWT for the mobile app
        internal_token = create_access_token({"sub": str(connection.user_id)})
        
        return {"access_token": internal_token, "token_type": "bearer", "email": email}

@router.get("/yandex/status")
def yandex_status(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check connection status."""
    conn = db.query(YandexConnections).filter(YandexConnections.user_id == current_user.id).first()
    if not conn:
        return {"status": "disconnected"}
    return {"status": "connected", "email": conn.email}

@router.delete("/yandex/disconnect")
def disconnect_yandex(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disconnects Yandex account by removing tokens."""
    db.query(YandexConnections).filter(YandexConnections.user_id == current_user.id).delete()
    db.commit()
    return {"status": "disconnected"}
