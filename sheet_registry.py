"""Manages sheets.json — maps "YYYY-MM" keys to Google Sheet IDs."""

import json
from config import SHEETS_REGISTRY


def _load() -> dict:
    if SHEETS_REGISTRY.exists():
        return json.loads(SHEETS_REGISTRY.read_text())
    return {}


def _save(data: dict):
    SHEETS_REGISTRY.write_text(json.dumps(data, indent=2) + "\n")


def _key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def register(year: int, month: int, sheet_id: str):
    data = _load()
    data[_key(year, month)] = sheet_id
    _save(data)


def get_sheet_id(year: int, month: int) -> str | None:
    return _load().get(_key(year, month))


def list_all() -> dict:
    return _load()
