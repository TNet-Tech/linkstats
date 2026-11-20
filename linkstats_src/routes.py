from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chacc_api.database import get_async_db

from .context_factory import get_module_context
from .models import Click, Count, DayCount, LinkStats, RecentClick, TopLink

router = APIRouter()


async def _get_link(code: str):
    """Look the code up through the shortlinks module's service."""
    context = get_module_context()
    get_by_code = context.get_service("shortlinks.get_by_code") if context else None
    if get_by_code is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The shortlinks module is not loaded.")
    link = await get_by_code(code)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No short link with code '{code}'.")
    return link


async def _top_counts(db: AsyncSession, column, link_id: int, limit: int) -> list[Count]:
    rows = (
        await db.execute(
            select(column, func.count(Click.id).label("n"))
            .where(Click.link_id == link_id)
            .group_by(column)
            .order_by(func.count(Click.id).desc(), column)
            .limit(limit)
        )
    ).all()
    return [Count(name=name, clicks=n) for name, n in rows]


@router.get("/top", response_model=list[TopLink])
async def top_links(
    limit: int = Query(5, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """Short links ranked by number of clicks."""
    rows = (
        await db.execute(
            select(
                Click.code,
                func.count(Click.id).label("clicks"),
                func.count(distinct(Click.ip_hash)).label("unique"),
            )
            .group_by(Click.code)
            .order_by(func.count(Click.id).desc(), Click.code)
            .limit(limit)
        )
    ).all()

    context = get_module_context()
    get_by_code = context.get_service("shortlinks.get_by_code") if context else None
    result = []
    for code, clicks, unique in rows:
        link = await get_by_code(code) if get_by_code else None
        result.append(
            TopLink(
                code=code,
                target_url=link.target_url if link else None,
                clicks=clicks,
                unique_visitors=unique,
            )
        )
    return result


@router.get("/{code}", response_model=LinkStats)
async def link_stats(
    code: str,
    top: int = Query(5, ge=1, le=50, description="How many referers / agents to list."),
    db: AsyncSession = Depends(get_async_db),
):
    """Click statistics for one short link."""
    link = await _get_link(code)

    total, unique, first, last = (
        await db.execute(
            select(
                func.count(Click.id),
                func.count(distinct(Click.ip_hash)),
                func.min(Click.created_at),
                func.max(Click.created_at),
            ).where(Click.link_id == link.id)
        )
    ).one()

    day = func.date(Click.created_at)
    by_day = (
        await db.execute(
            select(day, func.count(Click.id)).where(Click.link_id == link.id).group_by(day).order_by(day)
        )
    ).all()

    return LinkStats(
        code=link.code,
        target_url=link.target_url,
        total_clicks=total,
        unique_visitors=unique,
        first_click=first,
        last_click=last,
        by_day=[DayCount(day=d, clicks=n) for d, n in by_day],
        top_referers=await _top_counts(db, Click.referer_host, link.id, top),
        top_agents=await _top_counts(db, Click.agent_family, link.id, top),
    )


@router.get("/{code}/recent", response_model=list[RecentClick])
async def recent_clicks(
    code: str,
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    """The latest clicks on a short link, newest first."""
    link = await _get_link(code)
    clicks = (
        await db.execute(
            select(Click)
            .where(Click.link_id == link.id)
            .order_by(Click.created_at.desc(), Click.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        RecentClick(
            at=c.created_at,
            agent_family=c.agent_family,
            referer_host=c.referer_host,
            user_agent=c.user_agent,
        )
        for c in clicks
    ]
