"""Pydantic models.

Two groups of models live here:

1. **Content schema** (``docs/design.md`` §6): the YAML authored in ``content/``.
   A discriminated union on the ``type`` field selects the flow-specific model:
   ``knowledge | coding | rehearsal | walkthrough | template``.

2. **Runtime data model** (``docs/design.md`` §7): users, items, progress/SRS,
   captured rehearsal answers, and sessions.

Field names deliberately mirror the YAML keys in design.md §6 so that ingest
works directly on the real content files other authors write in parallel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Shared content pieces
# ---------------------------------------------------------------------------

Status = Literal["draft", "reviewed", "approved"]
Difficulty = Literal["easy", "medium", "hard"]
_DIFFICULTY_MAP = {
    1: "easy", 2: "medium", 3: "hard",
    "1": "easy", "2": "medium", "3": "hard",
}


class Source(BaseModel):
    """A researched citation attached to an item (design.md §6 `sources`).

    Also reused for a template's ``synthesized_from`` entries, where only
    ``title``/``url`` are present, so ``supports`` is optional.
    """

    model_config = ConfigDict(extra="allow")

    title: str
    url: Optional[str] = None
    supports: Optional[str] = None


class ContentBase(BaseModel):
    """Shared front-matter for the four served flow types (design.md §6).

    ``template`` items do NOT inherit this — they carry a different front-matter
    (see :class:`Template`).
    """

    model_config = ConfigDict(extra="allow")

    id: str
    category: str
    skill: Optional[str] = None
    difficulty: Difficulty = "medium"
    status: Status = "draft"

    @field_validator("difficulty", mode="before")
    @classmethod
    def _normalize_difficulty(cls, v):
        """Accept legacy numeric 1/2/3 and coerce to easy/medium/hard labels."""
        if isinstance(v, str) and v.lower() in ("easy", "medium", "hard"):
            return v.lower()
        return _DIFFICULTY_MAP.get(v, "medium")
    # `question` is the single canonical display field for every served flow
    # (knowledge question / coding problem / rehearsal prompt). `walkthrough`
    # additionally uses `scenario` as its headline. See design.md §6 conventions.
    question: Optional[str] = None
    # `question` is a SHORT title (used in lists); `description` is the full problem
    # statement shown on the card (mainly for coding, e.g. the LeetCode prompt).
    description: Optional[str] = None
    # progressive hints for the Anki-style recall flow: shown one at a time before
    # the answer is revealed ("think about X" → "now consider Y" → …).
    hints: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    # Is this actually asked in AI-engineering interviews? Generic DSA from the old
    # leetcode repo is mostly False; field-guide-sourced coding is True. Drives which
    # coding questions surface first. None = untriaged.
    ai_relevant: Optional[bool] = None
    source_refs: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# knowledge
# ---------------------------------------------------------------------------


class KnowledgeAnswer(BaseModel):
    model_config = ConfigDict(extra="allow")

    short: str
    key_points: list[str] = Field(default_factory=list)


class MCQOption(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str
    correct: bool = False


class MCQExercise(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["mcq"]
    stem: str
    options: list[MCQOption]
    explain: Optional[str] = None


class OrderExercise(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["order"]
    prompt: str
    steps: list[str]


class FillExercise(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["fill"]
    template: str
    blanks: list[str]
    chips: list[str] = Field(default_factory=list)


class MatchExercise(BaseModel):
    """concept↔definition matching (design.md §4). No YAML example given, kept lax."""

    model_config = ConfigDict(extra="allow")

    kind: Literal["match"]
    prompt: Optional[str] = None
    pairs: list[dict] = Field(default_factory=list)


class RecallExercise(BaseModel):
    """flashcard recall flip (design.md §4). Self-marked, SRS backbone."""

    model_config = ConfigDict(extra="allow")

    kind: Literal["recall"]
    prompt: Optional[str] = None


class ExplainExercise(BaseModel):
    """typed answer graded by an LLM against ``answer.key_points``."""

    model_config = ConfigDict(extra="allow")

    kind: Literal["explain"]


Exercise = Annotated[
    Union[
        MCQExercise,
        OrderExercise,
        FillExercise,
        MatchExercise,
        RecallExercise,
        ExplainExercise,
    ],
    Field(discriminator="kind"),
]


class Knowledge(ContentBase):
    type: Literal["knowledge"] = "knowledge"
    answer: KnowledgeAnswer
    follow_ups: list[str] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# coding
# ---------------------------------------------------------------------------


class Complexity(BaseModel):
    model_config = ConfigDict(extra="allow")

    time: Optional[str] = None
    space: Optional[str] = None


class CodingAnswer(BaseModel):
    model_config = ConfigDict(extra="allow")

    # algorithm subtype
    approach: Optional[str] = None
    pseudocode: Optional[str] = None
    complexity: Optional[Complexity] = None
    # implementation subtype (extension_points may be plain strings or {level, ...} objects)
    design_approach: Optional[str] = None
    extension_points: list[Union[str, dict]] = Field(default_factory=list)


class Coding(ContentBase):
    type: Literal["coding"] = "coding"
    subtype: Literal["algorithm", "implementation", "ml-coding"] = "algorithm"
    # display field is the inherited `question` (the problem statement)
    answer: CodingAnswer
    follow_ups: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# rehearsal
# ---------------------------------------------------------------------------


class Scaffold(BaseModel):
    model_config = ConfigDict(extra="allow")

    format: Optional[str] = None
    slots: list[str] = Field(default_factory=list)


class Rehearsal(ContentBase):
    type: Literal["rehearsal"] = "rehearsal"
    # display field is the inherited `question` (the behavioral/project prompt)
    probes: list[str] = Field(default_factory=list)
    scaffold: Optional[Scaffold] = None
    rubric: list[str] = Field(default_factory=list)
    example_structure: Optional[str] = None  # STAR skeleton, not a real story
    example: Optional[str] = None  # legacy alias, tolerated
    your_project: Optional[str] = None  # project-deep-dive only


# ---------------------------------------------------------------------------
# walkthrough
# ---------------------------------------------------------------------------


class WalkthroughStep(BaseModel):
    model_config = ConfigDict(extra="allow")

    phase: str
    prompt: str
    reference: Optional[str] = None


class Walkthrough(ContentBase):
    type: Literal["walkthrough"] = "walkthrough"
    template_ref: Optional[str] = None
    scenario: str
    steps: list[WalkthroughStep] = Field(default_factory=list)
    diagram: Optional[str] = None  # mermaid


# ---------------------------------------------------------------------------
# template (system-design study artifact) — distinct front-matter
# ---------------------------------------------------------------------------


class Template(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    category: str
    type: Literal["template"] = "template"
    title: str
    # design.md §6 shows no `status` on templates; default to draft and let a
    # reviewer opt them into serving (see friction note in the handoff).
    status: Status = "draft"
    synthesized_from: list[Source] = Field(default_factory=list)
    # design.md §6 shows plain strings, but authored templates enrich each entry
    # into a {phase, do: [...]} object — accept both.
    framework: list[Union[str, dict]] = Field(default_factory=list)
    skeleton_diagram: Optional[str] = None
    key_patterns: list[str] = Field(default_factory=list)  # authored addition
    generates: list[str] = Field(default_factory=list)


ContentItem = Annotated[
    Union[Knowledge, Coding, Rehearsal, Walkthrough, Template],
    Field(discriminator="type"),
]


class ContentFile(BaseModel):
    """Validation wrapper so a bare YAML mapping can be parsed as the union."""

    item: ContentItem


def parse_content(data: dict) -> ContentItem:
    """Validate a raw YAML mapping into the correct flow model."""
    return ContentFile(item=data).item


# ---------------------------------------------------------------------------
# Runtime data model (design.md §7)
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(BaseModel):
    id: str = "me"  # single user for now
    created_at: datetime = Field(default_factory=_now)
    xp: int = 0
    streak: int = 0
    daily_goal: int = 1
    last_active: Optional[datetime] = None


class Item(BaseModel):
    """An ingested, approved content item as stored at runtime.

    Keeps identifying fields hot for querying/selection and stashes the full
    validated content under ``content`` for the flow renderer to use.
    """

    id: str
    type: str
    category: str
    skill: Optional[str] = None
    difficulty: str = "medium"
    status: str = "approved"
    content: dict  # full model_dump of the ContentItem


class Progress(BaseModel):
    """Per user/item SRS state (design.md §7 `progress`)."""

    user_id: str
    item_id: str
    ease: float = 2.5
    interval: int = 0  # days
    due: Optional[datetime] = None
    last_grade: Optional[int] = None
    reps: int = 0


class RehearsalAnswer(BaseModel):
    """Per-user captured rehearsal answer + grades over time (design.md §7 `answers`)."""

    user_id: str
    item_id: str
    text: str
    grades: list[int] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


SessionState = Literal["active", "completed"]


class SessionResult(BaseModel):
    item_id: str
    grade: Optional[int] = None
    correct: Optional[bool] = None


class Session(BaseModel):
    """A ~7–15 exercise run (design.md §2, §7 `sessions`)."""

    id: str
    user_id: str
    skill: Optional[str] = None
    item_ids: list[str] = Field(default_factory=list)
    cursor: int = 0
    state: SessionState = "active"
    xp_earned: int = 0
    results: list[SessionResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None
