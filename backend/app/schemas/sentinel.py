import uuid
from datetime import datetime

from pydantic import BaseModel


class ScenarioResponse(BaseModel):
    id: uuid.UUID
    source: str
    difficulty: str
    package_name: str
    registry: str
    version_from: str | None = None
    version_to: str | None = None
    # The 6 inspection dimensions
    identity_data: dict
    timing_data: dict
    shape_data: dict
    behavior_data: dict
    flow_data: dict
    context_data: dict
    # Stats
    total_inspections: int = 0
    correct_rate: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScenarioListResponse(BaseModel):
    items: list[ScenarioResponse]
    total: int
    page: int
    per_page: int


class VerdictRequest(BaseModel):
    session_id: str
    verdict: str  # safe, suspicious, malicious
    confidence: float
    attack_type_guess: str | None = None
    evidence_notes: dict | None = None
    time_taken_secs: float | None = None
    tools_used: list[str] | None = None


class VerdictResponse(BaseModel):
    is_correct: bool
    score: int
    was_malicious: bool
    attack_name: str | None = None
    attack_type: str | None = None
    postmortem: str | None = None
    real_cve: str | None = None
    real_cvss: float | None = None
    # Updated player stats
    player_level: int
    player_title: str
    player_streak: int
    player_total_score: int
    player_detection_rate: float | None = None


class PlayerStatsResponse(BaseModel):
    session_id: str
    level: int
    title: str
    total_inspections: int
    correct_flags: int
    false_flags: int
    missed_attacks: int
    total_score: int
    streak: int
    best_streak: int
    detection_rate: float | None
    false_positive_rate: float | None
    vote_weight: float


class LeaderboardEntry(BaseModel):
    session_id: str
    title: str
    level: int
    total_score: int
    detection_rate: float | None
    best_streak: int


class SentinelStatsResponse(BaseModel):
    total_scenarios: int
    total_inspections: int
    total_players: int
    avg_detection_rate: float | None
    leaderboard: list[LeaderboardEntry]
