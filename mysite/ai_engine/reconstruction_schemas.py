from typing import Literal
from pydantic import BaseModel, Field


class EvidenceReference(BaseModel):

    chunk_id: int = Field(ge=1)

    quote: str = Field(
        min_length=1,
        max_length=800
    )


class KnowledgeCandidate(BaseModel):

    item_type: Literal[
        "DECISION",
        "TASK",
        "OWNERSHIP",
        "RISK",
        "BLOCKER",
        "DEPENDENCY",
        "OPEN_QUESTION",
        "NEXT_ACTION",
        "CONTACT",
        "OTHER",
    ]

    title: str = Field(
        min_length=3,
        max_length=255
    )

    description: str = Field(
        min_length=5
    )

    priority: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]

    confidence_score: float = Field(
        ge=0,
        le=1
    )

    assigned_to_username: str | None = None

    due_date: str | None = None

    evidence: list[EvidenceReference] = Field(
        min_length=1,
        max_length=5
    )


class ConflictCandidate(BaseModel):

    item_a_index: int = Field(ge=0)

    item_b_index: int = Field(ge=0)

    description: str = Field(
        min_length=5
    )


class KnowledgeReconstructionResult(BaseModel):

    project_summary: str

    items: list[KnowledgeCandidate] = Field(
        default_factory=list,
        max_length=30
    )

    possible_conflicts: list[ConflictCandidate] = Field(
        default_factory=list,
        max_length=20
    )