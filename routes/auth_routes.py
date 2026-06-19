from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import Utilisateur, RefreshToken
from auth.dependencies import get_db, get_current_user
from auth.security import verify_password, hash_password, create_access_token, create_refresh_token, decode_token
from schemas.auth_schema import RefreshRequest, TokenOut
from schemas.utilisateur_schema import UtilisateurOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _save_refresh_token(db: Session, utilisateur_id: int, token: str, expires_at) -> None:
    db.query(RefreshToken).filter(RefreshToken.utilisateur_id == utilisateur_id).delete()
    db.flush()
    db.add(RefreshToken(utilisateur_id=utilisateur_id, token=token, expires_at=expires_at))
    db.commit()


@router.post("/login", response_model=TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Utilisateur).filter(Utilisateur.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )
    data = {"sub": str(user.utilisateurId)}
    access_token = create_access_token(data)
    refresh_token, expires_at = create_refresh_token(data)
    _save_refresh_token(db, user.utilisateurId, refresh_token, expires_at)
    return TokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token invalide ou expiré",
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        utilisateur_id = payload.get("sub")
        if not utilisateur_id:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # Vérifier que le token existe en base
    token_db = db.query(RefreshToken).filter(
        RefreshToken.utilisateur_id == int(utilisateur_id),
        RefreshToken.token == body.refresh_token,
    ).first()
    if not token_db:
        raise credentials_exception

    user = db.query(Utilisateur).filter(
        Utilisateur.utilisateurId == int(utilisateur_id)
    ).first()
    if not user or not user.is_active:
        raise credentials_exception

    data = {"sub": str(user.utilisateurId)}
    access_token = create_access_token(data)
    refresh_token, expires_at = create_refresh_token(data)
    _save_refresh_token(db, user.utilisateurId, refresh_token, expires_at)
    return TokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
def logout(current_user: Utilisateur = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(RefreshToken).filter(
        RefreshToken.utilisateur_id == current_user.utilisateurId
    ).delete()
    db.commit()


@router.get("/me", response_model=UtilisateurOut)
def me(current_user: Utilisateur = Depends(get_current_user)):
    result = UtilisateurOut.model_validate(current_user)
    result.service_nom = current_user.service.nom if current_user.service else None
    return result


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.put("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.mot_de_passe):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit contenir au moins 6 caractères")
    current_user.mot_de_passe = hash_password(body.new_password)
    db.commit()
