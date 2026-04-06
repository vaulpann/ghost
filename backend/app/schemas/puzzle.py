import uuid
from datetime import datetime

from pydantic import BaseModel


class PuzzleResponse(BaseModel):
    id: uuid.UUID
    vulnerability_id: uuid.UUID
    game_type: str
    title: str
    flavor_text: str
    level_data: dict
    difficulty: int
    par_time_secs: int | None = None
    created_at: datetime
    # Stats
    total_attempts: int = 0
    solve_rate: float | None = None  # 0.0-1.0
    avg_solve_time: float | None = None
    # Enriched
    package_name: str | None = None
    package_registry: str | None = None

    model_config = {"from_attributes": True}


class PuzzleListResponse(BaseModel):
    items: list[PuzzleResponse]
    total: int
    page: int
    per_page: int


class PuzzleAttemptRequest(BaseModel):
    session_id: str
    solved: bool
    time_taken_secs: float | None = None
    moves: int | None = None
    solution_path: dict | None = None


class PuzzleAttemptResponse(BaseModel):
    id: uuid.UUID
    puzzle_id: uuid.UUID
    solved: bool
    time_taken_secs: float | None
    moves: int | None
    created_at: datetime
    # Puzzle stats after attempt
    total_attempts: int
    solve_rate: float
    avg_solve_time: float | None
    your_rank: int | None = None  # where you placed in solve time


class PuzzleStatsResponse(BaseModel):
    total_puzzles: int
    total_attempts: int
    total_solves: int
    overall_solve_rate: float | None
    game_type_breakdown: dict  # {game_type: {puzzles: N, solve_rate: X}}
