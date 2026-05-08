from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Utilisateur, Service
from schemas import UtilisateurCreate, UtilisateurOut
from auth.security import hash_password
from auth.dependencies import get_db

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])


@router.get("/", response_model=List[UtilisateurOut])
def list_utilisateurs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Utilisateur).offset(skip).limit(limit).all()


@router.get("/{utilisateur_id}", response_model=UtilisateurOut)
def get_utilisateur(utilisateur_id: int, db: Session = Depends(get_db)):
    u = db.query(Utilisateur).filter(Utilisateur.utilisateurId == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return u


@router.post("/", response_model=UtilisateurOut, status_code=201)
def create_utilisateur(data: UtilisateurCreate, db: Session = Depends(get_db)):
    existing = db.query(Utilisateur).filter(Utilisateur.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    if not db.query(Service).filter(Service.serviceId == data.service_id).first():
        raise HTTPException(status_code=400, detail="Service introuvable")
    payload = data.model_dump()
    payload["mot_de_passe"] = hash_password(payload["mot_de_passe"])
    u = Utilisateur(**payload, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.delete("/{utilisateur_id}", status_code=204)
def delete_utilisateur(utilisateur_id: int, db: Session = Depends(get_db)):
    u = db.query(Utilisateur).filter(Utilisateur.utilisateurId == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    db.delete(u)
    db.commit()
