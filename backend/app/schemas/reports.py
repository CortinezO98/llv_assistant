from datetime import date
from pydantic import BaseModel, Field


class ReportFilters(BaseModel):
    days: int = 30
    date_from: date | None = None
    date_to: date | None = None
    channel: str | None = None
    session_status: str | None = None
    agent_id: int | None = None
    products: list[str] = Field(default_factory=list)
    location: str | None = None
    payment_status: str | None = None


class InsightItem(BaseModel):
    name: str
    count: int


class ReportSummaryResponse(BaseModel):
    period: dict
    conversations: dict
    agents: dict
    appointments: dict
    sales: dict
    channels: dict
    satisfaction: dict
    patients: dict
    insights: dict
    filters: dict
