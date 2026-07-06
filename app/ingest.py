"""Content ingest (design.md §6, §8).

Walk ``content/**/*.yaml``, validate each file against the content models, and
load ONLY ``status: approved`` items into a :class:`~app.store.Store`.

Draft/reviewed items are skipped (not served) and never crash the run — this is
important because authors work on drafts in parallel. Validation errors on a
single file are logged and skipped too, so one bad file can't take down ingest.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.models import Item, parse_content
from app.store import Store

logger = logging.getLogger("app.ingest")


@dataclass
class IngestReport:
    approved: int = 0
    drafts: int = 0  # anything with status != approved (draft/reviewed)
    errors: int = 0
    error_files: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.approved + self.drafts + self.errors


def _iter_yaml_files(root: Path):
    yield from sorted(root.rglob("*.yaml"))
    yield from sorted(root.rglob("*.yml"))


def ingest_dir(
    content_dir: str | Path, store: Store, include_drafts: bool = False
) -> IngestReport:
    """Ingest items under ``content_dir`` into ``store``.

    By default only ``status: approved`` items are served. When ``include_drafts``
    is true (set via ``INGEST_INCLUDE_DRAFTS`` on the sandbox deploy), draft/reviewed
    items are loaded too — so you can review authored content from the phone before
    approving it.
    """
    root = Path(content_dir)
    report = IngestReport()

    if not root.exists():
        logger.warning("content dir %s does not exist; nothing ingested", root)
        return report

    for path in _iter_yaml_files(root):
        try:
            raw = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            report.errors += 1
            report.error_files.append(str(path))
            logger.warning("YAML parse error in %s: %s", path, exc)
            continue

        if not isinstance(raw, dict):
            report.errors += 1
            report.error_files.append(str(path))
            logger.warning("skipping %s: top-level YAML is not a mapping", path)
            continue

        # Non-item config files (e.g. content/skills.yaml) have no `type` — skip, not error.
        if "type" not in raw:
            logger.debug("skipping non-item yaml %s (no type key)", path)
            continue

        try:
            content = parse_content(raw)
        except ValidationError as exc:
            report.errors += 1
            report.error_files.append(str(path))
            logger.warning("validation error in %s: %s", path, exc)
            continue

        status = getattr(content, "status", "draft")
        if status != "approved":
            report.drafts += 1
            if not include_drafts:
                logger.debug("skipping %s (status=%s)", content.id, status)
                continue

        store.put_item(_to_item(content))
        report.approved += 1

    logger.info(
        "ingest complete: %d approved, %d skipped (draft/reviewed), %d errors",
        report.approved,
        report.drafts,
        report.errors,
    )
    return report


def _to_item(content) -> Item:
    return Item(
        id=content.id,
        type=content.type,
        category=content.category,
        skill=getattr(content, "skill", None),
        difficulty=getattr(content, "difficulty", "medium"),
        status=getattr(content, "status", "approved"),
        content=content.model_dump(mode="json"),
    )
