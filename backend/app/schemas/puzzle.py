import uuid
from datetime import datetime

from pydantic import BaseModel


class PuzzleOption(BaseModel):
    text: str
    is_correct: bool = False  # Only included in results, stripped from puzzle response


class PuzzleResponse(BaseModel):
    id: uuid.UUID
    vulnerability_id: uuid.UUID
    challenge_type: str
    title: str
    scenario: str
    options: list[dict]  # text only — no is_correct until after voting
    difficulty: int
    created_at: datetime
    vote_count: int = 0
    # Enriched
    package_name: str | None = None
    package_registry: str | None = None
    vuln_title: str | None = None

    model_config = {"from_attributes": True}


class PuzzleResultResponse(BaseModel):
    """Returned after voting — includes correct answer and consensus."""
    id: uuid.UUID
    title: str
    scenario: str
    options: list[dict]  # includes is_correct
    explanation: str
    consensus: dict  # {option_index: vote_count, ...}
    total_votes: int
    user_was_correct: bool


class PuzzleVoteRequest(BaseModel):
    selected_index: int
    confidence: float
    time_taken_secs: float | None = None
    session_id: str


class PuzzleListResponse(BaseModel):
    items: list[PuzzleResponse]
    total: int
    page: int
    per_page: int


class PuzzleStatsResponse(BaseModel):
    total_puzzles: int
    total_votes: int
    avg_accuracy: float | None
    consensus_rate: float | None  # % of puzzles where >60% agree
