from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents import analytics_agent
from app.api.common import hospital_of
from app.core.deps import require_roles
from app.core.responses import ok
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])
staff = require_roles("hospital", "admin")


def _scope(db: Session, user: User):
    """Hospitals see their own numbers; admins see everything."""
    if user.role == "hospital":
        h = hospital_of(db, user)
        return h.id if h else None
    return None


@router.get("/overview")
def overview(user: User = Depends(staff), db: Session = Depends(get_db)):
    return ok(analytics_agent.overview(db, _scope(db, user)), "Synthetic demo data")


@router.get("/blood-groups")
def blood_groups(user: User = Depends(staff), db: Session = Depends(get_db)):
    return ok(analytics_agent.blood_group_demand(db, _scope(db, user)), "Synthetic demo data")


@router.get("/invitations")
def invitations(user: User = Depends(staff), db: Session = Depends(get_db)):
    return ok(analytics_agent.invitation_stats(db, _scope(db, user)), "Synthetic demo data")
