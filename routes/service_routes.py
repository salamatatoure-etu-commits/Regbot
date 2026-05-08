from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Service
from schemas import ServiceOut
from schemas.service_schema import ServiceCreate
from auth.dependencies import get_db

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("/", response_model=List[ServiceOut])
def list_services(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Service).offset(skip).limit(limit).all()


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.serviceId == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    return service


@router.post("/", response_model=ServiceOut, status_code=201)
def create_service(data: ServiceCreate, db: Session = Depends(get_db)):
    existing = db.query(Service).filter(Service.nom == data.nom).first()
    if existing:
        raise HTTPException(status_code=400, detail="Service déjà existant")
    service = Service(**data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=204)
def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.serviceId == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    db.delete(service)
    db.commit()
