"""Ingest skips drafts and loads only approved items (design.md §6)."""

from pathlib import Path

from app.ingest import ingest_dir
from app.store import InMemoryStore

FIXTURES = Path(__file__).parent / "fixtures"


def test_ingest_skips_drafts_and_loads_approved():
    store = InMemoryStore()
    report = ingest_dir(FIXTURES, store)

    # 5 approved fixtures (one per flow type) + 1 draft.
    assert report.approved == 5
    assert report.drafts == 1
    assert report.errors == 0

    loaded_ids = {i.id for i in store.list_items()}
    assert "rag-what-is-rag" in loaded_ids
    assert "rag-draft-item" not in loaded_ids  # draft skipped

    # every served item is approved and carries its full content payload
    for item in store.list_items():
        assert item.status == "approved"
        assert item.content["id"] == item.id


def test_ingest_missing_dir_is_safe():
    store = InMemoryStore()
    report = ingest_dir(FIXTURES / "does-not-exist", store)
    assert report.total == 0
    assert store.list_items() == []


def test_ingest_all_flow_types_present():
    store = InMemoryStore()
    ingest_dir(FIXTURES, store)
    types = {i.type for i in store.list_items()}
    assert types == {"knowledge", "coding", "rehearsal", "walkthrough", "template"}
