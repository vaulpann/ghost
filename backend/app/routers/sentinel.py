import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sentinel import SentinelPlayer, SentinelScenario, SentinelVerdict
from app.schemas.sentinel import (
    LeaderboardEntry,
    PlayerStatsResponse,
    ScenarioListResponse,
    ScenarioResponse,
    SentinelStatsResponse,
    VerdictRequest,
    VerdictResponse,
)

router = APIRouter(tags=["sentinel"])

LEVEL_TITLES = {
    1: "Dock Worker",
    2: "Inspector",
    3: "Analyst",
    4: "Investigator",
    5: "Sentinel",
    6: "Chief Sentinel",
}

TOOLS_BY_LEVEL = {
    1: ["identity", "timing"],
    2: ["identity", "timing", "shape"],
    3: ["identity", "timing", "shape", "behavior"],
    4: ["identity", "timing", "shape", "behavior", "flow"],
    5: ["identity", "timing", "shape", "behavior", "flow", "context"],
    6: ["identity", "timing", "shape", "behavior", "flow", "context"],
}


@router.get("/sentinel/scenarios", response_model=ScenarioListResponse)
async def list_scenarios(
    difficulty: str | None = None,
    source: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(SentinelScenario)
    count_query = select(func.count(SentinelScenario.id))

    if difficulty:
        query = query.where(SentinelScenario.difficulty == difficulty)
        count_query = count_query.where(SentinelScenario.difficulty == difficulty)
    if source:
        query = query.where(SentinelScenario.source == source)
        count_query = count_query.where(SentinelScenario.source == source)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(SentinelScenario.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )
    scenarios = result.scalars().all()

    items = []
    for s in scenarios:
        verdict_count = (await db.execute(
            select(func.count(SentinelVerdict.id)).where(SentinelVerdict.scenario_id == s.id)
        )).scalar() or 0
        correct_count = (await db.execute(
            select(func.count(SentinelVerdict.id)).where(
                SentinelVerdict.scenario_id == s.id,
                SentinelVerdict.is_correct == True  # noqa: E712
            )
        )).scalar() or 0

        resp = ScenarioResponse.model_validate(s)
        resp.total_inspections = verdict_count
        resp.correct_rate = round(correct_count / verdict_count, 3) if verdict_count > 0 else None
        items.append(resp)

    return ScenarioListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/sentinel/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: uuid.UUID,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SentinelScenario).where(SentinelScenario.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(404, "Scenario not found")

    # All 6 tools always available
    all_tools = ["identity", "timing", "shape", "behavior", "flow", "context"]

    data = {
        "id": str(scenario.id),
        "source": scenario.source,
        "difficulty": scenario.difficulty,
        "package_name": scenario.package_name,
        "registry": scenario.registry,
        "version_from": scenario.version_from,
        "version_to": scenario.version_to,
        "available_tools": all_tools,
        "tools": {
            "identity": scenario.identity_data,
            "timing": scenario.timing_data,
            "shape": scenario.shape_data,
            "behavior": scenario.behavior_data,
            "flow": scenario.flow_data,
            "context": scenario.context_data,
        },
    }

    return data


@router.post("/sentinel/scenarios/{scenario_id}/verdict", response_model=VerdictResponse)
async def submit_verdict(
    scenario_id: uuid.UUID,
    req: VerdictRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SentinelScenario).where(SentinelScenario.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(404, "Scenario not found")

    # If already submitted, return the existing result instead of erroring
    existing = await db.execute(
        select(SentinelVerdict).where(
            SentinelVerdict.scenario_id == scenario_id,
            SentinelVerdict.session_id == req.session_id,
        )
    )
    existing_verdict = existing.scalar_one_or_none()
    if existing_verdict:
        return VerdictResponse(
            is_correct=existing_verdict.is_correct,
            score=existing_verdict.score,
            was_malicious=scenario.is_malicious,
            attack_name=scenario.attack_name if scenario.is_malicious else None,
            attack_type=scenario.attack_type if scenario.is_malicious else None,
            postmortem=scenario.postmortem,
            real_cve=scenario.real_cve,
            real_cvss=scenario.real_cvss,
            player_level=1,
            player_title="Dock Worker",
            player_streak=0,
            player_total_score=0,
            player_detection_rate=None,
        )

    # Score the verdict
    is_correct = False
    score = 0

    if scenario.is_malicious:
        # Attack scenario — correct if flagged suspicious or malicious
        if req.verdict in ("suspicious", "malicious"):
            is_correct = True
            base_score = 100 if req.verdict == "malicious" else 50
            # Bonus for correct attack type
            if req.attack_type_guess and req.attack_type_guess == scenario.attack_type:
                base_score += 50
            # Bonus for confidence
            base_score = int(base_score * req.confidence)
            # Bonus for speed
            if req.time_taken_secs and req.time_taken_secs < 60:
                base_score += 25
            # Difficulty multiplier
            diff_mult = {"tutorial": 1, "easy": 1.5, "medium": 2, "hard": 3, "expert": 5}
            score = int(base_score * diff_mult.get(scenario.difficulty, 1))
        else:
            # Missed a real attack
            score = -50
    else:
        # Benign scenario — correct if marked safe
        if req.verdict == "safe":
            is_correct = True
            score = 25  # Less points for correctly identifying benign (it's easier)
        else:
            # False positive
            score = -25

    # Save verdict
    verdict = SentinelVerdict(
        scenario_id=scenario_id,
        session_id=req.session_id,
        verdict=req.verdict,
        confidence=req.confidence,
        attack_type_guess=req.attack_type_guess,
        evidence_notes=req.evidence_notes,
        time_taken_secs=req.time_taken_secs,
        tools_used=req.tools_used,
        is_correct=is_correct,
        score=score,
    )
    db.add(verdict)

    # Update player stats
    player = await _get_or_create_player(db, req.session_id)
    player.total_inspections += 1
    player.total_score += max(score, 0)

    if is_correct:
        if scenario.is_malicious:
            player.correct_flags += 1
        player.streak += 1
        if player.streak > player.best_streak:
            player.best_streak = player.streak
    else:
        if scenario.is_malicious and req.verdict == "safe":
            player.missed_attacks += 1
        elif not scenario.is_malicious and req.verdict != "safe":
            player.false_flags += 1
        player.streak = 0

    # Recalculate rates
    total_attacks = player.correct_flags + player.missed_attacks
    if total_attacks > 0:
        player.detection_rate = round(player.correct_flags / total_attacks, 3)
    total_flags = player.correct_flags + player.false_flags
    if total_flags > 0:
        player.false_positive_rate = round(player.false_flags / total_flags, 3)

    # Level up check
    old_level = player.level
    if player.total_inspections >= 50 and player.detection_rate and player.detection_rate >= 0.8:
        player.level = 6
    elif player.total_inspections >= 30 and player.detection_rate and player.detection_rate >= 0.7:
        player.level = 5
    elif player.total_inspections >= 20:
        player.level = 4
    elif player.total_inspections >= 10:
        player.level = 3
    elif player.total_inspections >= 5:
        player.level = 2

    player.title = LEVEL_TITLES.get(player.level, "Dock Worker")

    # Vote weight increases with accuracy
    if player.detection_rate and player.total_inspections >= 10:
        player.vote_weight = round(0.5 + (player.detection_rate * 1.5), 2)

    await db.commit()

    return VerdictResponse(
        is_correct=is_correct,
        score=score,
        was_malicious=scenario.is_malicious,
        attack_name=scenario.attack_name if scenario.is_malicious else None,
        attack_type=scenario.attack_type if scenario.is_malicious else None,
        postmortem=scenario.postmortem,
        real_cve=scenario.real_cve,
        real_cvss=scenario.real_cvss,
        player_level=player.level,
        player_title=player.title,
        player_streak=player.streak,
        player_total_score=player.total_score,
        player_detection_rate=player.detection_rate,
    )


@router.get("/sentinel/player/{session_id}", response_model=PlayerStatsResponse)
async def get_player_stats(session_id: str, db: AsyncSession = Depends(get_db)):
    player = await _get_or_create_player(db, session_id)
    await db.commit()
    return PlayerStatsResponse(
        session_id=player.session_id,
        level=player.level,
        title=player.title,
        total_inspections=player.total_inspections,
        correct_flags=player.correct_flags,
        false_flags=player.false_flags,
        missed_attacks=player.missed_attacks,
        total_score=player.total_score,
        streak=player.streak,
        best_streak=player.best_streak,
        detection_rate=player.detection_rate,
        false_positive_rate=player.false_positive_rate,
        vote_weight=player.vote_weight,
    )


@router.get("/sentinel/stats", response_model=SentinelStatsResponse)
async def get_sentinel_stats(db: AsyncSession = Depends(get_db)):
    total_scenarios = (await db.execute(select(func.count(SentinelScenario.id)))).scalar() or 0
    total_inspections = (await db.execute(select(func.count(SentinelVerdict.id)))).scalar() or 0
    total_players = (await db.execute(select(func.count(SentinelPlayer.session_id)))).scalar() or 0

    avg_detection = (await db.execute(
        select(func.avg(SentinelPlayer.detection_rate)).where(SentinelPlayer.detection_rate.isnot(None))
    )).scalar()

    # Leaderboard — top 10 by score
    lb_result = await db.execute(
        select(SentinelPlayer)
        .where(SentinelPlayer.total_inspections >= 3)
        .order_by(SentinelPlayer.total_score.desc())
        .limit(10)
    )
    leaderboard = [
        LeaderboardEntry(
            session_id=p.session_id[:8] + "...",
            title=p.title,
            level=p.level,
            total_score=p.total_score,
            detection_rate=p.detection_rate,
            best_streak=p.best_streak,
        )
        for p in lb_result.scalars().all()
    ]

    return SentinelStatsResponse(
        total_scenarios=total_scenarios,
        total_inspections=total_inspections,
        total_players=total_players,
        avg_detection_rate=round(avg_detection, 3) if avg_detection else None,
        leaderboard=leaderboard,
    )


async def _get_or_create_player(db: AsyncSession, session_id: str) -> SentinelPlayer:
    result = await db.execute(
        select(SentinelPlayer).where(SentinelPlayer.session_id == session_id)
    )
    player = result.scalar_one_or_none()
    if not player:
        player = SentinelPlayer(session_id=session_id)
        db.add(player)
        await db.flush()
    return player
