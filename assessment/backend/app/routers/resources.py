from datetime import date
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import require_staff
from app.models import Resource, ResourceCategoryEnum, Booking, BookingStatusEnum
from app.schemas import ResourceCreate, ResourceOut

router = APIRouter(prefix=f"{settings.API_PREFIX}/resources", tags=["resources"])


@router.get("/", response_model=list[ResourceOut], summary="List / search resources")
def list_resources(
    category: Optional[Literal["ROOM", "SUITE", "HALL"]] = Query(None),
    check_in: Optional[date] = Query(None),
    check_out: Optional[date] = Query(None),
    min_rate: Optional[float] = Query(None, ge=0),
    max_rate: Optional[float] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    """List resources, optionally filtering by category, rate and real-time
    availability for a requested date range (excludes resources that already
    have a conflicting CONFIRMED booking)."""
    query = db.query(Resource).filter(Resource.is_available.is_(True))

    if category:
        query = query.filter(Resource.category == ResourceCategoryEnum(category))
    if min_rate is not None:
        query = query.filter(Resource.daily_rate >= min_rate)
    if max_rate is not None:
        query = query.filter(Resource.daily_rate <= max_rate)

    resources = query.order_by(Resource.category, Resource.daily_rate).all()

    if check_in and check_out:
        if check_out <= check_in:
            raise HTTPException(status_code=400, detail="check_out must be after check_in")

        # Resources holding any CONFIRMED booking overlapping the window are unavailable.
        busy_ids = (
            db.query(Booking.resource_id)
            .filter(
                Booking.status == BookingStatusEnum.CONFIRMED,
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
            .distinct()
            .subquery()
        )
        resources = [r for r in resources if r.id not in [row[0] for row in db.query(busy_ids).all()]]

    return resources


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


@router.post(
    "/",
    response_model=ResourceOut,
    status_code=201,
    summary="Create a resource (STAFF/ADMIN only)",
    dependencies=[Depends(require_staff)],
)
def create_resource(body: ResourceCreate, db: Session = Depends(get_db)):
    resource = Resource(
        name=body.name,
        category=ResourceCategoryEnum(body.category),
        daily_rate=body.daily_rate,
        is_available=body.is_available,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource
