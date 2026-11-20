"""Turns shortlinks visit events into stored clicks."""
import hashlib
import logging
from urllib.parse import urlparse

from chacc_api.database import async_session

from .models import Click

logger = logging.getLogger("linkstats")

LISTENER_NAME = "linkstats"
DEFAULT_IP_SALT = "linkstats-demo-salt"

# Order matters: Edge and Opera also say "Chrome", Chrome also says "Safari".
_AGENT_RULES = [
    ("bot", ("bot", "crawler", "spider", "preview")),
    ("curl", ("curl/",)),
    ("httpie", ("httpie/",)),
    ("python", ("python-requests", "python-httpx", "aiohttp")),
    ("postman", ("postmanruntime",)),
    ("edge", ("edg/",)),
    ("opera", ("opr/",)),
    ("chrome", ("chrome/", "crios/")),
    ("firefox", ("firefox/", "fxios/")),
    ("safari", ("safari/",)),
]


def agent_family(user_agent: str | None) -> str:
    ua = (user_agent or "").lower()
    if not ua:
        return "unknown"
    for family, needles in _AGENT_RULES:
        if any(n in ua for n in needles):
            return family
    return "other"


def referer_host(referer: str | None) -> str:
    if not referer:
        return "direct"
    host = urlparse(referer if "://" in referer else f"http://{referer}").hostname
    return (host or "direct").removeprefix("www.")


def hash_ip(ip: str | None, salt: str) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


def make_recorder(salt: str):
    """Build the visit listener that shortlinks calls after each redirect."""

    async def record_click(event) -> None:
        async with async_session() as db:
            db.add(
                Click(
                    link_id=event.link_id,
                    code=event.code,
                    user_agent=(event.user_agent or "")[:512] or None,
                    agent_family=agent_family(event.user_agent),
                    referer=(event.referer or "")[:1024] or None,
                    referer_host=referer_host(event.referer),
                    ip_hash=hash_ip(event.client_ip, salt),
                    created_at=event.visited_at,
                )
            )
            await db.commit()

    return record_click
