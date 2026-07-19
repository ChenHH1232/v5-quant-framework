# Unicode Path CLI Argument Policy V1

## Problem

Some V5 evidence paths use the Chinese database directory `数据库`. On Windows PowerShell, Chinese CLI arguments or captured terminal output can become mojibake if the caller, subprocess or console encoding is not aligned.

This has already produced false registry path failures where the real files existed but the stored evidence path was corrupted.

## Policy

- Prefer `src/v5/paths.py` constants for generated database paths.
- Prefer config-file paths over long CLI path arguments when a command needs several data files.
- For generated JSON and CSV, read with `utf-8-sig` when accepting external files and write with `utf-8`.
- For Python CLI calls in PowerShell, set `PYTHONIOENCODING=utf-8` when output may contain non-ASCII paths.
- Do not store mojibake fallback paths in `docs/governance/status_registry.json`.
- Add or run registry consistency tests after changing evidence paths.

## Current Repair

The status registry path entries for highway operating data and gas/water panels were repaired from mojibake paths to canonical `数据库/...` paths.

Guard test:

- `tests/test_status_registry_consistency.py`

Shared path constants:

- `src/v5/paths.py`

## PM Rule

Encoding defects are workflow defects, not research evidence. A missing evidence path caused by mojibake must be repaired before any PM decision uses that registry entry.
