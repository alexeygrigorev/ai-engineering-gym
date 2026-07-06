"""Schema validation round-trips for every flow type (design.md §6)."""

from pathlib import Path

import yaml

from app.models import (
    Coding,
    Knowledge,
    Rehearsal,
    Template,
    Walkthrough,
    parse_content,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return yaml.safe_load((FIXTURES / name).read_text())


def test_knowledge_roundtrip():
    item = parse_content(_load("knowledge_approved.yaml"))
    assert isinstance(item, Knowledge)
    assert item.type == "knowledge"
    assert item.answer.key_points
    kinds = [e.kind for e in item.exercises]
    assert kinds == ["mcq", "order", "fill", "explain"]
    # round-trip: dump and re-parse yields an equal model
    assert parse_content(item.model_dump()) == item


def test_coding_roundtrip():
    item = parse_content(_load("coding_approved.yaml"))
    assert isinstance(item, Coding)
    assert item.subtype == "algorithm"
    assert item.answer.complexity.time == "O(1) per op"
    assert parse_content(item.model_dump()) == item


def test_rehearsal_roundtrip():
    item = parse_content(_load("rehearsal_approved.yaml"))
    assert isinstance(item, Rehearsal)
    assert item.scaffold.format == "STAR"
    assert item.rubric
    assert parse_content(item.model_dump()) == item


def test_walkthrough_roundtrip():
    item = parse_content(_load("walkthrough_approved.yaml"))
    assert isinstance(item, Walkthrough)
    assert [s.phase for s in item.steps] == [
        "clarify",
        "high-level",
        "deep-dive",
        "tradeoffs",
    ]
    assert item.diagram.startswith("graph LR")
    assert parse_content(item.model_dump()) == item


def test_template_roundtrip():
    item = parse_content(_load("template_approved.yaml"))
    assert isinstance(item, Template)
    assert item.generates == ["walkthrough"]
    assert len(item.synthesized_from) == 2
    assert parse_content(item.model_dump()) == item
