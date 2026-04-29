from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session as DBSession

from app.core.security import decode_token
from app.db.models.agent import Agent
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_agent(
    token: str = Depends(oauth2_scheme),
    db: DBSession = Depends(get_db),
) -> Agent:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    agent_id = int(payload.get("sub", 0))
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.is_active == 1).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agente no encontrado")
    return agent


def require_admin(agent: Agent = Depends(get_current_agent)) -> Agent:
    if agent.role not in ("admin", "supervisor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol admin o supervisor")
    return agent


def require_supervisor(agent: Agent = Depends(get_current_agent)) -> Agent:
    if agent.role not in ("admin", "supervisor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol supervisor o admin")
    return agent


def require_agent_or_above(agent: Agent = Depends(get_current_agent)) -> Agent:
    """Cualquier rol autenticado puede acceder."""
    return agent
