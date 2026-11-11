"""
Pydantic Schemas for Multi-Device Authentication and User Management.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    consent_accepted: bool = Field(..., description="User biometric consent confirmation")
    device_id: Optional[str] = Field(default=None, max_length=128)
    device_name: Optional[str] = Field(default=None, max_length=255)
    platform: Optional[str] = Field(default="android", max_length=64)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    device_id: Optional[str] = Field(default=None, max_length=128)
    device_name: Optional[str] = Field(default=None, max_length=255)
    platform: Optional[str] = Field(default="android", max_length=64)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16)
    device_id: Optional[str] = Field(default=None, max_length=128)


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    device_id: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    pseudonym_id: str
    role: str = "researcher"
    consent_accepted: bool
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    token_type: str = "bearer"
    device_id: Optional[str] = None
    user: UserResponse


class DeviceSessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    device_id: str
    device_name: Optional[str] = None
    platform: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: datetime
    is_revoked: bool


class ConsentUpdate(BaseModel):
    consent_accepted: bool
