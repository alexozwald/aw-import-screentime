from __future__ import annotations

from datetime import datetime, timedelta
from datetime import tzinfo as dt_tzinfo
from pathlib import Path
from typing import Iterator, Optional, Sequence

from aw_core.models import Event

from aw_import_screentime.__main__ import (
    APPLE_EPOCH_OFFSET,
    cf_to_dt,
    connect_readonly,
    enrich_events_with_titles,
)


def knowledgec_db_path() -> Path:
    return Path.home() / "Library" / "Application Support" / "Knowledge" / "knowledgeC.db"


def iter_knowledgec_events(
    db_path: Path,
    *,
    tzinfo: dt_tzinfo,
    since: Optional[datetime],
) -> Iterator[Event]:
    """Yield ActivityWatch Events from knowledgeC.db /app/usage stream."""
    if not db_path.exists():
        return

    since_cf: Optional[float] = None
    if since is not None:
        since_cf = since.timestamp() - APPLE_EPOCH_OFFSET

    query = """
        SELECT ZVALUESTRING, ZSTARTDATE, ZENDDATE
        FROM ZOBJECT
        WHERE ZSTREAMNAME = '/app/usage'
          AND ZVALUESTRING IS NOT NULL
          AND ZENDDATE > ZSTARTDATE
    """
    params: list[float] = []
    if since_cf is not None:
        query += " AND ZENDDATE > ?"
        params.append(since_cf)
    query += " ORDER BY ZSTARTDATE ASC"

    with connect_readonly(db_path) as conn:
        for app, start_cf, end_cf in conn.execute(query, params):
            start_dt = cf_to_dt(start_cf, tzinfo)
            end_dt = cf_to_dt(end_cf, tzinfo)
            duration = end_dt - start_dt
            if duration.total_seconds() > 0:
                yield Event(timestamp=start_dt, duration=duration, data={"app": app})


def build_macos_events(
    *,
    tzinfo: dt_tzinfo,
    since: Optional[datetime],
    storefronts: Sequence[str],
) -> list[Event]:
    """Decode knowledgeC.db → enrich titles → return list of Events."""
    db_path = knowledgec_db_path()
    events = list(iter_knowledgec_events(db_path, tzinfo=tzinfo, since=since))
    if events:
        enrich_events_with_titles(events, storefronts=storefronts)
    return events
