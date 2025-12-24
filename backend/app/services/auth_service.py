"""
Authentication Service
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserLogin, TokenData


class AuthService:
    """Authentication service"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Tạo JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return TokenData(username=username)
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[dict]:
        """Authenticate user và trả về user info nếu thành công"""
        user = UserRepository.get_by_username(db, login_data.username)
        if not user:
            return None
        
        if not UserRepository.verify_password(login_data.password, user.password_hash):
            return None
        
        # Update last_login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "experience_points": user.experience_points
        }

