from datetime import date
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, transactional_session
from app.deps import get_current_user, require_staff
from app.models import (
    Booking,
    BookingStatusEnum,
    Resource,
    ResourceCategoryEnum,
    User,
)
from app.schemas import BookingCreate, BookingOut

router = APIRouter(prefix=f"{settings.API_PREFIX}/bookings", tags=["bookings"])


def _to_out(booking: Booking, db: Session) -> BookingOut:
    out = BookingOut.model_validate(booking)
    resource = booking.resource or db.query(Resource).filter(Resource.id == booking.resource_id).first()
    out.resource_name = resource.name if resource else None
    return out


@router.post(
    "/",
    response_model=BookingOut,
    status_code=201,
    summary="Create a booking (date-conflict checked, price calculated)",
)
def create_booking(
    body: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Business rules:

    1. The resource must exist and be marked available.
    2. The stay must be at least one night (check_out > check_in).
    3. No overlapping CONFIRMED booking may exist for the resource.
    4. total_price = nights * resource.daily_rate, persisted atomically.
    """
    resource = db.query(Resource).filter(Resource.id == body.resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if not resource.is_available:
        raise HTTPException(status_code=409, detail="Resource is currently unavailable")

    nights = (body.check_out - body.check_in).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    conflict = (
        db.query(Booking)
        .filter(
            Booking.resource_id == resource.id,
            Booking.status == BookingStatusEnum.CONFIRMED,
            Booking.check_in < body.check_out,
            Booking.check_out > body.check_in,
        )
        .with_for_update()
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Resource is already booked {conflict.check_in} -> {conflict.check_out}. "
                "Choose different dates."
            ),
        )

    total_price = nights * float(resource.daily_rate)

    with transactional_session(db):
        booking = Booking(
            resource_id=resource.id,
            user_id=current_user.id,
            check_in=body.check_in,
            check_out=body.check_out,
            total_price=total_price,
            status=BookingStatusEnum.CONFIRMED,
        )
        db.add(booking)

    db.refresh(booking)
    return _to_out(booking, db)


@router.get(
    "/my-reservations",
    response_model=list[BookingOut],
    summary="Reservations for the authenticated user",
)
def my_reservations(
    status_filter: Optional[Literal["CONFIRMED", "CANCELLED"]] = Query(None, alias="status"),
    category: Optional[Literal["ROOM", "SUITE", "HALL"]] = Query(None),
    check_in_from: Optional[date] = Query(None),
    check_in_to: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Filtered reservations belonging to the current user only."""
    query = db.query(Booking).filter(Booking.user_id == current_user.id)

    if status_filter:
        query = query.filter(Booking.status == BookingStatusEnum(status_filter))
    if check_in_from:
        query = query.filter(Booking.check_in >= check_in_from)
    if check_in_to:
        query = query.filter(Booking.check_in <= check_in_to)
    if category:
        query = query.join(Resource).filter(Resource.category == ResourceCategoryEnum(category))

    bookings = query.order_by(Booking.check_in.desc()).all()
    return [_to_out(b, db) for b in bookings]


@router.get(
    "/",
    response_model=list[BookingOut],
    summary="All bookings (STAFF/ADMIN only)",
    dependencies=[Depends(require_staff)],
)
def list_bookings(
    status_filter: Optional[Literal["CONFIRMED", "CANCELLED"]] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(Booking)
    if status_filter:
        query = query.filter(Booking.status == BookingStatusEnum(status_filter))
    bookings = query.order_by(Booking.created_at.desc()).all()
    return [_to_out(b, db) for b in bookings]


@router.patch(
    "/{booking_id}/cancel",
    response_model=BookingOut,
    summary="Cancel a booking",
)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # A customer may only cancel their own bookings; staff/admin may cancel any.
    if booking.user_id != current_user.id and current_user.role.value == "CUSTOMER":
        raise HTTPException(status_code=403, detail="You can only cancel your own bookings")
    if booking.status == BookingStatusEnum.CANCELLED:
        raise HTTPException(status_code=409, detail="Booking is already cancelled")

    with transactional_session(db):
        booking.status = BookingStatusEnum.CANCELLED

    db.refresh(booking)
    return _to_out(booking, db)
