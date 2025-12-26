"""
User Schemas (Pydantic)
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """Schema để tạo user mới"""
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Schema để login"""
    username: str
    password: str


class UserResponse(UserBase):
    """Schema để trả về user info"""
    id: int
    role: str = 'USER'
    experience_points: int
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema để update user"""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)


class UserRoleUpdate(BaseModel):
    """Schema để admin cập nhật role"""
    role: Literal['ADMIN', 'USER']


class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data"""
    username: Optional[str] = None


