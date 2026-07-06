"""In-app content review: thumbs up/down + comments on items.

Durable via DynamoDB when ``REVIEWS_TABLE`` is set (the Lambda deploy); falls back
to an in-memory dict for local dev / tests so nothing extra is needed to run. boto3
ships in the Lambda runtime, so it is imported lazily and never added as a dependency.

Reviews are the input to the approval loop: browse on the phone, thumbs-up to keep /
thumbs-down to cut / comment, then the /reviews export drives edits to the YAML content.
"""

from __future__ import annotations

import os
import time
from typing import Optional


def _ts() -> int:
    return int(time.time())


class InMemoryReviews:
    def __init__(self) -> None:
        self._d: dict[str, dict] = {}

    def get(self, item_id: str) -> Optional[dict]:
        return self._d.get(item_id)

    def put(self, item_id: str, verdict: str, comment: str) -> dict:
        rec = {"item_id": item_id, "verdict": verdict or "", "comment": comment or "", "updated_at": _ts()}
        self._d[item_id] = rec
        return rec

    def all(self) -> list[dict]:
        return sorted(self._d.values(), key=lambda r: r.get("updated_at", 0), reverse=True)


class DynamoReviews:
    def __init__(self, table_name: str) -> None:
        import boto3  # available in the Lambda runtime

        self._table = boto3.resource("dynamodb").Table(table_name)

    def get(self, item_id: str) -> Optional[dict]:
        return self._table.get_item(Key={"item_id": item_id}).get("Item")

    def put(self, item_id: str, verdict: str, comment: str) -> dict:
        rec = {"item_id": item_id, "verdict": verdict or "", "comment": comment or "", "updated_at": _ts()}
        self._table.put_item(Item=rec)
        return rec

    def all(self) -> list[dict]:
        items = self._table.scan().get("Items", [])
        return sorted(items, key=lambda r: r.get("updated_at", 0), reverse=True)


def get_review_store():
    table = os.environ.get("REVIEWS_TABLE")
    if table:
        try:
            return DynamoReviews(table)
        except Exception:  # boto3 missing / no creds locally → fall back
            pass
    return InMemoryReviews()
