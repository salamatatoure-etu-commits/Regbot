from pydantic import BaseModel, EmailStr
from typing import Optional
from models.enums import RoleEnum


class UtilisateurCreate(BaseModel):
    nom: str
    email: EmailStr
    mot_de_passe: str
    role: RoleEnum
    service_id: int


class UtilisateurOut(BaseModel):
    utilisateurId: int
    nom: str
    email: str
    role: RoleEnum
    service_id: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True
