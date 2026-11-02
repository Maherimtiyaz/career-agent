"""Schemas for opportunities and applications."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OpportunityCreate(BaseModel):
    title: str
    organization: str
    description: Optional[str] = None
    url: str
    source: str
    location: Optional[str] = None
    is_remote: bool = False
    stipend: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    source_id: Optional[str] = None


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    organization: str
    description: Optional[str]
    url: str
    source: str
    location: Optional[str]
    is_remote: bool
    stipend: Optional[str]
    deadline: Optional[str]
    tags: Optional[str]
    is_active: bool
    created_at: datetime


class ApplicationCreate(BaseModel):
    company: str
    role: str
    job_link: Optional[str] = None
    hr_contact: Optional[str] = None
    status: str = "applied"
    date_applied: Optional[str] = None
    notes: Optional[str] = None
    opportunity_id: Optional[uuid.UUID] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    hr_contact: Optional[str] = None
    notes: Optional[str] = None
    date_applied: Optional[str] = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company: str
    role: str
    job_link: Optional[str]
    hr_contact: Optional[str]
    status: str
    date_applied: Optional[str]
    notes: Optional[str]
    source: str
    opportunity_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
