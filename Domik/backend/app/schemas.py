from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LeadIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=40)
    email: Optional[EmailStr] = None
    guests: Optional[int] = Field(default=None, ge=1, le=30)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    message: Optional[str] = Field(default=None, max_length=2000)
    source: Optional[str] = "landing"


class LeadOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    guests: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    message: Optional[str] = None
    source: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class LeadStatusUpdate(BaseModel):
    status: str = Field(pattern="^(new|in_progress|confirmed|closed|spam)$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ContentItem(BaseModel):
    key: str
    value: str


class ContentBulk(BaseModel):
    items: list[ContentItem]
