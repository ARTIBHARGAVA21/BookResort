import enum
from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"


class ResourceCategoryEnum(str, enum.Enum):
    ROOM = "ROOM"
    SUITE = "SUITE"
    HALL = "HALL"


class BookingStatusEnum(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class ThreatLevelEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.CUSTOMER)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    category = Column(SAEnum(ResourceCategoryEnum), nullable=False)
    daily_rate = Column(Numeric(12, 2), nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)

    bookings = relationship("Booking", back_populates="resource")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    status = Column(SAEnum(BookingStatusEnum), nullable=False, default=BookingStatusEnum.CONFIRMED)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    resource = relationship("Resource", back_populates="bookings")
    user = relationship("User", back_populates="bookings")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False, default="POST")
    ip_address = Column(String(64), nullable=True)
    threat_level = Column(SAEnum(ThreatLevelEnum), nullable=False, default=ThreatLevelEnum.LOW)
    event = Column(String(255), nullable=False, default="REQUEST")
    details = Column(String(1024), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
