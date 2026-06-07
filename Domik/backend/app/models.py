from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Text, Boolean

from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(40), nullable=False)
    email = Column(String(255), nullable=True)
    guests = Column(Integer, nullable=True)
    date_from = Column(String(32), nullable=True)
    date_to = Column(String(32), nullable=True)
    message = Column(Text, nullable=True)
    source = Column(String(64), default="landing")
    status = Column(String(32), default="new")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class LandingContent(Base):
    __tablename__ = "landing_content"
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlockedDate(Base):
    __tablename__ = "blocked_dates"
    id = Column(Integer, primary_key=True)
    day = Column(Date, unique=True, nullable=False, index=True)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
