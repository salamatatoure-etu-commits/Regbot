import os
import bcrypt
from datetime import datetime, timedelta, UTC
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY    = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY manquant dans les variables d'environnement.")
ALGORITHM     = os.getenv("ALGORITHM", "HS256")
EXPIRE_MIN    = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_DAYS  = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"]  = datetime.now(UTC) + timedelta(minutes=EXPIRE_MIN)
    payload["type"] = "access"
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(days=REFRESH_DAYS)
    payload = data.copy()
    payload["exp"]  = expires_at
    payload["type"] = "refresh"
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), expires_at


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
