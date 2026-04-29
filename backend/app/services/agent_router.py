"""
app/services/agent_router.py

Distribución de carga entre los 6 agentes de LRV.
Algoritmo: round-robin ponderado por current_load (menor carga = prioridad).
"""
import logging

from sqlalchemy.orm import Session as DBSession

from app.db.models.agent import Agent
from app.db.models.session import Session

logger = logging.getLogger(__name__)


class AgentRouter:
    def __init__(self, db: DBSession):
        self.db = db

    def assign_agent(self, session: Session, location: str = "latam") -> Agent | None:
        """
        Asigna el agente disponible con menor carga del location correcto.
        Actualiza current_load y el campo assigned_agent_id de la sesión.
        """
        # Buscar agentes activos del location, ordenados por carga ascendente
        agents = (
            self.db.query(Agent)
            .filter(
                Agent.is_active == 1,
                Agent.location == location,
                Agent.role.in_(["agent", "supervisor"]),
            )
            .order_by(Agent.current_load.asc())
            .all()
        )

        if not agents:
            # Fallback: cualquier agente activo sin importar location
            agents = (
                self.db.query(Agent)
                .filter(Agent.is_active == 1)
                .order_by(Agent.current_load.asc())
                .all()
            )

        if not agents:
            logger.warning("No hay agentes disponibles para asignar. session_id=%s", session.id)
            return None

        selected = agents[0]

        # Actualizar carga
        selected.current_load = (selected.current_load or 0) + 1
        session.assigned_agent_id = selected.id
        session.status = "in_agent"
        self.db.flush()

        logger.info(
            "Agente asignado | agent=%s (id=%s) | load=%s | session=%s",
            selected.name,
            selected.id,
            selected.current_load,
            session.id,
        )
        return selected

    def release_agent(self, session: Session) -> None:
        """
        Libera al agente cuando se cierra una conversación.
        Decrementa current_load e incrementa total_closed.
        """
        if not session.assigned_agent_id:
            return

        agent = self.db.query(Agent).filter(Agent.id == session.assigned_agent_id).first()
        if agent:
            agent.current_load = max(0, (agent.current_load or 1) - 1)
            agent.total_closed = (agent.total_closed or 0) + 1
            self.db.flush()
            logger.info("Agente liberado | agent=%s | new_load=%s", agent.name, agent.current_load)
