# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                           # Install all dependencies (including dev)
black src/                        # Format code
mypy src/                         # Type-check
pytest                            # Run tests (none exist yet)

# Run the CLI directly
uv run aw-import-screentime --help
uv run aw-import-screentime devices
uv run aw-import-screentime events preview --device <device-id>
uv run aw-import-screentime events import --device <device-id>
uv run aw-import-screentime file <path-to-segb-file>
```

## Architecture

This is a CLI tool that reads Apple Screen Time telemetry (SEGB binary files from `~/Library/Biome/`) and imports it into [ActivityWatch](https://activitywatch.net/) as time-tracking events.

### Data Pipeline

```
~/Library/Biome/sync/sync.db      → device discovery (SQLite)
~/Library/Biome/streams/...       → SEGB files per device
    ↓ ccl-segb (binary parser)
AppInFocusEvent protobufs         → raw focus transitions
    ↓ stitch_intervals()
interval events                   → start/end pairs
    ↓ clip_events_since()
filtered events                   → --since filtering
    ↓ enrich_events_with_titles()  (iTunes Search API)
titled events
    ↓ EventSink
ActivityWatch server (HTTP)        → per-device buckets
```

### Key Design Patterns

- **EventSink protocol** (`src/aw_import_screentime/__main__.py`): `ActivityWatchSink` (real import) and `NullSink` (preview/dry-run) implement the same interface, selected by `cmd_events_preview` vs `cmd_events_import`.
- **Generator-based streaming**: `iter_app_in_focus_events()`, `iter_device_files()` use generators to minimize memory when processing large file sets.
- **stdout = JSON, stderr = logs**: All output is emitted as JSON via `emit_json()` so it can be piped to `jq`. Rich-formatted logs go to stderr only.
- **Protobuf typing under TYPE_CHECKING**: `AppInFocusEventT` protocol in `app_in_focus_extended_pb2.py` is only imported at type-check time to avoid runtime overhead.
- **Per-run title cache**: `_BUNDLE_TITLE_POS` / `_BUNDLE_TITLE_NEG` dicts cache iTunes API lookups within a single run.

### Entry Point

All CLI logic lives in `src/aw_import_screentime/__main__.py`. The Typer app has a top-level `events` subcommand group with `preview` and `import` subcommands, plus top-level `devices` and `file` commands.

`src/aw_import_screentime/__main__.zetavg.py` is an upstream reference version kept for diffing; it is not the active entry point.

### Protobuf

`app_in_focus_extended_pb2.py` is auto-generated from `app_in_focus_extended.proto`. Do not edit it by hand — regenerate with `protoc` if the schema changes.
