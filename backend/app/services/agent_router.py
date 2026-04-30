"""
app/services/agent_router.py

Distribución de carga entre agentes de LLV.

Objetivo:
- No asignar siempre al primer agente cuando varios tienen la misma carga.
- Priorizar agentes activos del mismo location del paciente.
- Si no hay agentes en ese location, usar cualquier agente activo.
- Elegir aleatoriamente entre los agentes con menor carga actual.
"""

import logging
import random

from sqlalchemy.orm import Session as DBSession

from app.db.models.agent import Agent
from app.db.models.session import Session

logger = logging.getLogger(__name__)


class AgentRouter:
    def __init__(self, db: DBSession):
        self.db = db

    def assign_agent(self, session: Session, location: str = "latam") -> Agent | None:
        """
        Asigna una conversación al agente disponible con menor carga.

        Regla principal:
        1. Busca agentes activos del mismo location.
        2. Si no encuentra, busca agentes activos globales.
        3. Calcula la menor carga actual.
        4. Si varios agentes tienen esa misma carga, escoge uno aleatoriamente.
        5. Incrementa current_load y marca la sesión como in_agent.
        """

        # 1. Buscar agentes activos del location del paciente
        agents = (
            self.db.query(Agent)
            .filter(
                Agent.is_active == 1,
                Agent.location == location,
                Agent.role.in_(["agent", "supervisor"]),
            )
            .all()
        )

        # 2. Fallback: cualquier agente activo con rol operativo
        if not agents:
            agents = (
                self.db.query(Agent)
                .filter(
                    Agent.is_active == 1,
                    Agent.role.in_(["agent", "supervisor"]),
                )
                .all()
            )

        if not agents:
            logger.warning(
                "No hay agentes disponibles para asignar. session_id=%s | location=%s",
                session.id,
                location,
            )
            return None

        # 3. Obtener menor carga actual
        min_load = min(agent.current_load or 0 for agent in agents)

        # 4. Candidatos con menor carga
        candidates = [
            agent
            for agent in agents
            if (agent.current_load or 0) == min_load
        ]

        # 5. Escoger aleatoriamente entre los menos cargados
        selected = random.choice(candidates)

        # 6. Actualizar carga y sesión
        selected.current_load = (selected.current_load or 0) + 1
        session.assigned_agent_id = selected.id
        session.status = "in_agent"

        self.db.flush()

        logger.info(
            "Agente asignado | agent=%s | id=%s | location=%s | load=%s | session=%s | candidates=%s",
            selected.name,
            selected.id,
            selected.location,
            selected.current_load,
            session.id,
            [a.id for a in candidates],
        )

        return selected

    def release_agent(self, session: Session) -> None:
        """
        Libera al agente cuando se cierra una conversación.

        - Decrementa current_load.
        - Incrementa total_closed.
        """
        if not session.assigned_agent_id:
            return

        agent = (
            self.db.query(Agent)
            .filter(Agent.id == session.assigned_agent_id)
            .first()
        )

        if not agent:
            logger.warning(
                "No se encontró agente para liberar. session_id=%s | assigned_agent_id=%s",
                session.id,
                session.assigned_agent_id,
            )
            return

        agent.current_load = max(0, (agent.current_load or 1) - 1)
        agent.total_closed = (agent.total_closed or 0) + 1

        self.db.flush()

        logger.info(
            "Agente liberado | agent=%s | id=%s | new_load=%s | total_closed=%s | session=%s",
            agent.name,
            agent.id,
            agent.current_load,
            agent.total_closed,
            session.id,
        )