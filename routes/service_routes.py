from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Service, Utilisateur
from models.document_model import Document
from models.bot_model import Bot
from models.conversation_model import Conversation
from schemas import ServiceOut
from schemas.service_schema import ServiceCreate, ServiceUpdate
from auth.dependencies import get_db, require_admin

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("/", response_model=List[ServiceOut])
def list_services(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    return db.query(Service).offset(skip).limit(limit).all()


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    service = db.query(Service).filter(Service.serviceId == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    return service


@router.post("/", response_model=ServiceOut, status_code=201)
def create_service(
    data: ServiceCreate,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    existing = db.query(Service).filter(Service.nom == data.nom).first()
    if existing:
        raise HTTPException(status_code=400, detail="Service déjà existant")
    service = Service(**data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.put("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    service = db.query(Service).filter(Service.serviceId == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    if data.nom and data.nom != service.nom:
        existing = db.query(Service).filter(Service.nom == data.nom).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ce nom de service existe déjà")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=204)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    service = db.query(Service).filter(Service.serviceId == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    db.query(Document).filter(Document.service_id == service_id).update({"service_id": None})
    db.query(Utilisateur).filter(Utilisateur.service_id == service_id).update({"service_id": None})
    db.query(Conversation).filter(Conversation.service_id == service_id).update({"service_id": None})
    db.query(Bot).filter(Bot.service_id == service_id).update({"service_id": None})
    db.delete(service)
    db.commit()
