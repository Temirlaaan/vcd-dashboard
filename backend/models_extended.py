# models_extended.py - Дополнительные модели для истории и заметок
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ActionType(str, Enum):
    """Типы действий для истории"""
    IP_ALLOCATED = "IP_ALLOCATED"
    IP_RELEASED = "IP_RELEASED"
    IP_RESERVED = "IP_RESERVED"
    IP_UNRESERVED = "IP_UNRESERVED"
    POOL_CREATED = "POOL_CREATED"
    POOL_DELETED = "POOL_DELETED"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    NOTE_ADDED = "NOTE_ADDED"
    NOTE_DELETED = "NOTE_DELETED"

class HistoryEntry(BaseModel):
    """Модель записи истории"""
    id: Optional[int] = None
    timestamp: datetime
    action_type: ActionType
    user: str
    ip_address: Optional[str] = None
    cloud_name: Optional[str] = None
    pool_name: Optional[str] = None
    organization: Optional[str] = None
    details: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None

class Note(BaseModel):
    """Модель заметки"""
    id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: str
    category: str  # "general", "maintenance", "issue", "info"
    priority: str  # "low", "medium", "high", "critical"
    title: str
    content: str
    ip_address: Optional[str] = None  # Если заметка относится к конкретному IP
    cloud_name: Optional[str] = None
    pool_name: Optional[str] = None
    tags: List[str] = []
    is_pinned: bool = False
    expires_at: Optional[datetime] = None  # Для временных заметок

class ExportRequest(BaseModel):
    """Модель запроса на экспорт"""
    format: str  # "excel", "pdf", "csv"
    include_history: bool = False
    include_notes: bool = False
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    clouds: Optional[List[str]] = None
    pools: Optional[List[str]] = None