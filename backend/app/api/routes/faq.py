"""Rutas CRUD de la base de conocimiento FAQ."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent, require_admin
from app.db.models.agent import Agent
from app.db.models.messaging import FAQ
from app.db.session import get_db

router = APIRouter(prefix="/faq", tags=["faq"])


class FAQCreate(BaseModel):
    category: str
    question: str
    answer: str


class FAQUpdate(BaseModel):
    category: str | None = None
    question: str | None = None
    answer: str | None = None
    is_active: int | None = None


@router.get("/")
def list_faq(category: str | None = None, db: DBSession = Depends(get_db), _: Agent = Depends(get_current_agent)):
    q = db.query(FAQ)
    if category:
        q = q.filter(FAQ.category == category)
    items = q.order_by(FAQ.category, FAQ.id).all()
    return [{"id": f.id, "category": f.category, "question": f.question, "answer": f.answer, "is_active": f.is_active} for f in items]


@router.post("/", status_code=201)
def create_faq(body: FAQCreate, db: DBSession = Depends(get_db), _: Agent = Depends(require_admin)):
    item = FAQ(category=body.category, question=body.question, answer=body.answer)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id}


@router.patch("/{faq_id}")
def update_faq(faq_id: int, body: FAQUpdate, db: DBSession = Depends(get_db), _: Agent = Depends(require_admin)):
    item = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ no encontrada")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(item, field, val)
    db.commit()
    return {"ok": True}


@router.delete("/{faq_id}")
def delete_faq(faq_id: int, db: DBSession = Depends(get_db), _: Agent = Depends(require_admin)):
    item = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ no encontrada")
    db.delete(item)
    db.commit()
    return {"ok": True}
