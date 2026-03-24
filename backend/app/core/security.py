from cryptography.fernet import Fernet
from app.core.config import settings
from jose import jwt, JWTError
from datetime import datetime, timedelta
import base64

# Pad or truncate the encryption key to 32 bytes and base64 encode it for Fernet
_key = settings.ENCRYPTION_KEY.ljust(32, '0')[:32].encode('utf-8')
_fernet_key = base64.urlsafe_b64encode(_key)
cipher_suite = Fernet(_fernet_key)

def encrypt_token(token: str) -> str:
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=365) # long living for mobile
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
