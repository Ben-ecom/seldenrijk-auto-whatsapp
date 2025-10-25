"""
GDPR consent and data management models.
Defines database tables for consent tracking, data exports, and deletions.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ConsentRecord(BaseModel):
    """Consent record for GDPR compliance."""
    id: Optional[str] = None
    contact_id: str
    consent_type: str  # marketing, analytics, communication
    granted: bool
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None

class DataExport(BaseModel):
    """Data export request record."""
    id: Optional[str] = None
    contact_id: str
    email: str
    status: str  # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    expires_at: datetime
    download_url: Optional[str] = None
    file_name: Optional[str] = None
    error: Optional[str] = None

class DataDeletion(BaseModel):
    """Data deletion request record."""
    id: Optional[str] = None
    contact_id: str
    status: str  # pending, processing, completed, failed
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
