from datetime import datetime, date
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    scopes: list[str] = []


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: Optional[Literal["ADMIN", "STAFF", "CUSTOMER"]] = "CUSTOMER"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: str
    created_at: datetime


# --------------------------------------------------------------------------- #
# Resources
# --------------------------------------------------------------------------- #
class ResourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: Literal["ROOM", "SUITE", "HALL"]
    daily_rate: float = Field(gt=0)
    is_available: bool = True


class ResourceCreate(ResourceBase):
    pass


class ResourceOut(ResourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# --------------------------------------------------------------------------- #
# Bookings
# --------------------------------------------------------------------------- #
class BookingCreate(BaseModel):
    resource_id: int
    check_in: date
    check_out: date

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v, info):
        if info.data.get("check_in") and v <= info.data["check_in"]:
            raise ValueError("check_out must be after check_in")
        return v


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_id: int
    user_id: int
    check_in: date
    check_out: date
    total_price: float
    status: str
    created_at: datetime
    resource_name: Optional[str] = None


# --------------------------------------------------------------------------- #
# Security / Audit
# --------------------------------------------------------------------------- #
class AuditLogCreate(BaseModel):
    endpoint: str
    method: str = "POST"
    ip_address: Optional[str] = None
    threat_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    event: str = "SECURITY_EVENT"
    details: Optional[str] = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    endpoint: str
    method: str
    ip_address: Optional[str] = None
    threat_level: str
    event: str
    details: Optional[str] = None
    timestamp: datetime
    user_email: Optional[str] = None


class AuditLogQuery(BaseModel):
    threat_level: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None
    endpoint: Optional[str] = None
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=500)


class ThreatAssessment(BaseModel):
    threat_level: str
    reasons: list[str] = []
