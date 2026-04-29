from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.security import create_access_token, verify_password
from app.db.models.agent import Agent
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent_id: int
    name: str
    role: str


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DBSession = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.email == body.email, Agent.is_active == 1).first()
    if not agent or not verify_password(body.password, agent.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    token = create_access_token({"sub": str(agent.id), "role": agent.role})
    return TokenResponse(
        access_token=token,
        agent_id=agent.id,
        name=agent.name,
        role=agent.role,
    )
