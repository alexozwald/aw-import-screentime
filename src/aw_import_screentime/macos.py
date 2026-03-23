from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Optional

from aw_import_screentime.__main__ import (
    connect_readonly,
    sync_db_path,
)

logger = logging.getLogger("aw_import_screentime")


def local_stream_dir() -> Path:
    return (
        Path.home()
        / "Library"
        / "Biome"
        / "streams"
        / "restricted"
        / "App.InFocus"
        / "local"
    )


def get_mac_device_id(db_path: Path) -> Optional[str]:
    """Return the local Mac's device_identifier from sync.db (platform=3)."""
    if not db_path.exists():
        logger.warning("Sync DB not found at %s", db_path)
        return None
    with connect_readonly(db_path) as conn:
        conn.row_factory = lambda cur, row: row[0]
        rows = conn.execute(
            "SELECT DISTINCT device_identifier FROM DevicePeer WHERE platform = ?;",
            (3,),
        ).fetchall()
    if not rows:
        logger.warning("No platform=3 device found in sync.db")
        return None
    return rows[0]


def iter_local_files() -> Iterator[Path]:
    """Yield regular SEGB files in App.InFocus/local/, oldest→newest by mtime."""
    base = local_stream_dir()
    try:
        files = [
            p
            for p in base.iterdir()
            if p.is_file() and not p.name.startswith(".") and p.name != "tombstone"
        ]
    except (FileNotFoundError, PermissionError) as e:
        logger.warning("Skipping local stream dir: %s", e)
        return iter(())
    files.sort(key=lambda p: p.stat().st_mtime)
    logger.debug("Enumerated local files: %d file(s)", len(files))
    return iter(files)


def tail_local_files(*, limit: int) -> list[Path]:
    """
    Return the most recent SEGB files from App.InFocus/local/, limited by `limit`.
    Does NOT filter by mtime — clip at event level via --since.
    """
    files = list(iter_local_files())
    if limit > 0:
        files = files[-limit:]
    return files
