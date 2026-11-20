from datetime import date, datetime

from chacc_api import ChaCCBaseModel
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, Integer, String


class Click(ChaCCBaseModel):
    """One visit of a short link. `created_at` is the time of the click."""

    __tablename__ = "linkstats_clicks"

    # The link lives in the shortlinks module's table: this is the cross-module dependency.
    link_id = Column(Integer, ForeignKey("shortlinks_links.id"), index=True, nullable=False)
    code = Column(String(32), index=True, nullable=False)
    user_agent = Column(String(512), nullable=True)
    agent_family = Column(String(32), nullable=False, default="other")
    referer = Column(String(1024), nullable=True)
    referer_host = Column(String(255), nullable=False, default="direct")
    ip_hash = Column(String(64), nullable=True, index=True)


# --- API schemas ---


class Count(BaseModel):
    name: str
    clicks: int


class DayCount(BaseModel):
    day: date
    clicks: int


class LinkStats(BaseModel):
    code: str
    target_url: str
    total_clicks: int
    unique_visitors: int
    first_click: datetime | None
    last_click: datetime | None
    by_day: list[DayCount]
    top_referers: list[Count]
    top_agents: list[Count]


class TopLink(BaseModel):
    code: str
    target_url: str | None
    clicks: int
    unique_visitors: int


class RecentClick(BaseModel):
    at: datetime
    agent_family: str
    referer_host: str
    user_agent: str | None
