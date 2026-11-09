"""Auth dependencies. Role checks are enforced here on the backend, not just in the UI."""
import uuid
from collections.abc import Callable

try:
    import jwt
    JWTError = jwt.PyJWTError
except ImportError:
    from jose import jwt
    JWTError = jwt.JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Donor, Hospital, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_access_token(creds.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


def require_roles(*roles: str) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this resource")
        return user

    return checker


def get_current_hospital(
    user: User = Depends(require_roles("hospital")), db: Session = Depends(get_db)
) -> Hospital:
    hospital = db.query(Hospital).filter(Hospital.user_id == user.id).first()
    if hospital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hospital profile not found")
    return hospital


def get_current_donor(
    user: User = Depends(require_roles("donor")), db: Session = Depends(get_db)
) -> Donor:
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    if donor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor profile not found")
    return donor
