from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from models import Utilisateur
from models.base import SessionLocal
from auth.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        utilisateur_id = payload.get("sub")
        if utilisateur_id is None:
            raise credentials_exception
        utilisateur_id = int(utilisateur_id)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(Utilisateur).filter(
        Utilisateur.utilisateurId == utilisateur_id
    ).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
