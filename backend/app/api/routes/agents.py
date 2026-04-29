"""Rutas de gestión de agentes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent, require_admin
from app.core.security import hash_password
from app.db.models.agent import Agent
from app.db.session import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "agent"
    location: str = "latam"


class AgentUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    location: str | None = None
    is_active: int | None = None


@router.get("/")
def list_agents(db: DBSession = Depends(get_db), _: Agent = Depends(get_current_agent)):
    agents = db.query(Agent).order_by(Agent.name).all()
    return [
        {
            "id": a.id, "name": a.name, "email": a.email, "role": a.role,
            "location": a.location, "is_active": a.is_active,
            "current_load": a.current_load, "total_closed": a.total_closed,
        }
        for a in agents
    ]


@router.post("/", status_code=201)
def create_agent(body: AgentCreate, db: DBSession = Depends(get_db), _: Agent = Depends(require_admin)):
    existing = db.query(Agent).filter(Agent.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    agent = Agent(
        name=body.name, email=body.email,
        password_hash=hash_password(body.password),
        role=body.role, location=body.location,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"id": agent.id, "name": agent.name, "email": agent.email}


@router.patch("/{agent_id}")
def update_agent(agent_id: int, body: AgentUpdate, db: DBSession = Depends(get_db), _: Agent = Depends(require_admin)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(agent, field, val)
    db.commit()
    return {"ok": True}
