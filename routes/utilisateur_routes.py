from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from models import Utilisateur, Service
from schemas import UtilisateurCreate, UtilisateurOut
from auth.security import hash_password
from auth.dependencies import get_db, require_admin

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])


@router.get("/", response_model=List[UtilisateurOut])
def list_utilisateurs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    return db.query(Utilisateur).offset(skip).limit(limit).all()


@router.get("/{utilisateur_id}", response_model=UtilisateurOut)
def get_utilisateur(
    utilisateur_id: int,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    u = db.query(Utilisateur).filter(Utilisateur.utilisateurId == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return u


@router.post("/", response_model=UtilisateurOut, status_code=201)
def create_utilisateur(
    data: UtilisateurCreate,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
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
def delete_utilisateur(
    utilisateur_id: int,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    u = db.query(Utilisateur).filter(Utilisateur.utilisateurId == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    db.delete(u)
    db.commit()


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.put("/{utilisateur_id}/toggle-active", response_model=UtilisateurOut)
def toggle_active(
    utilisateur_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_admin),
):
    if utilisateur_id == current_user.utilisateurId:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas modifier votre propre statut")
    u = db.query(Utilisateur).filter(Utilisateur.utilisateurId == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    u.is_active = not u.is_active
    db.commit()
    db.refresh(u)
    return u


@router.put("/{utilisateur_id}/reset-password", status_code=204)
def reset_user_password(
    utilisateur_id: int,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    u = db.query(Utilisateur).filter(Utilisateur.utilisateurId == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")
    u.mot_de_passe = hash_password(body.new_password)
    db.commit()
