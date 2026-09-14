from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building
from app.schemas import BuildingOut

router = APIRouter(prefix="/api", tags=["buildings"])


@router.get("/buildings", response_model=list[BuildingOut])
def list_buildings(db: Session = Depends(get_db)):
    """Open to everyone, including guests -- this is the self-service
    building/room directory (requirement: non-CS students find their way
    around without needing to ask staff)."""
    return db.query(Building).all()
