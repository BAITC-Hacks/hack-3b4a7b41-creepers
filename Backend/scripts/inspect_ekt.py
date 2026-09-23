"""Inspect only documented endpoints; never print headers, credentials or values.

Run from Backend: .venv/Scripts/python scripts/inspect_ekt.py
Reports JSON key paths and value types, enough to begin a real schema mapping.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.ekt_client import EktClient
from app.config import Settings
from app.core.errors import AppError
from app.core.logging import configure_logging


def shape(value, depth=0):
    if depth > 6:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: shape(item, depth + 1) for key, item in value.items()
                if not any(part in key.casefold() for part in ("password", "secret", "auth", "token", "username"))}
    if isinstance(value, list):
        return {"type": "array", "length": len(value), "samples": [shape(item, depth + 1) for item in value[:2]]}
    return type(value).__name__


async def main():
    configure_logging()
    client = EktClient(Settings())
    failed = False
    try:
        for path, params in [("products", None), ("products", {"page": 2}), ("products/detail", {"id": "515291"})]:
            try:
                data = await client.request_json(path, params)
                print(json.dumps({"endpoint": path, "params": params, "shape": shape(data)}, ensure_ascii=True, indent=2))
            except AppError as exc:
                failed = True
                print(json.dumps({"endpoint": path, "error": exc.code}))
    finally:
        await client.close()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
