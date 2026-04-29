from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent
from app.db.models.agent import Agent
from app.db.session import get_db
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/usage")
def get_plan_usage(db: DBSession = Depends(get_db), _: Agent = Depends(get_current_agent)):
    svc = NotificationService(db)
    return svc.get_current_usage()
