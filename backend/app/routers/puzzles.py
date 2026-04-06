import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.puzzle import Puzzle, PuzzleVote
from app.models.vulnerability import Vulnerability
from app.models.vulnerability_scan import VulnerabilityScan
from app.models.package import Package
from app.schemas.puzzle import (
    PuzzleListResponse,
    PuzzleResponse,
    PuzzleResultResponse,
    PuzzleStatsResponse,
    PuzzleVoteRequest,
)

router = APIRouter(tags=["puzzles"])


@router.get("/puzzles", response_model=PuzzleListResponse)
async def list_puzzles(
    challenge_type: str | None = None,
    vulnerability_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            Puzzle.id,
            Puzzle.vulnerability_id,
            Puzzle.challenge_type,
            Puzzle.title,
            Puzzle.scenario,
            Puzzle.options,
            Puzzle.difficulty,
            Puzzle.created_at,
            func.count(PuzzleVote.id).label("vote_count"),
            Package.name.label("package_name"),
            Package.registry.label("package_registry"),
            Vulnerability.title.label("vuln_title"),
        )
        .join(Vulnerability, Puzzle.vulnerability_id == Vulnerability.id)
        .join(Package, Vulnerability.package_id == Package.id)
        .outerjoin(PuzzleVote, PuzzleVote.puzzle_id == Puzzle.id)
        .group_by(Puzzle.id, Package.name, Package.registry, Vulnerability.title)
    )
    count_query = select(func.count(Puzzle.id))

    if challenge_type:
        query = query.where(Puzzle.challenge_type == challenge_type)
        count_query = count_query.where(Puzzle.challenge_type == challenge_type)
    if vulnerability_id:
        query = query.where(Puzzle.vulnerability_id == vulnerability_id)
        count_query = count_query.where(Puzzle.vulnerability_id == vulnerability_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Puzzle.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = result.all()

    items = []
    for r in rows:
        # Strip is_correct from options before sending
        safe_options = [{"text": o.get("text", ""), "index": i} for i, o in enumerate(r.options)]
        items.append(PuzzleResponse(
            id=r.id, vulnerability_id=r.vulnerability_id,
            challenge_type=r.challenge_type, title=r.title,
            scenario=r.scenario, options=safe_options,
            difficulty=r.difficulty, created_at=r.created_at,
            vote_count=r.vote_count,
            package_name=r.package_name, package_registry=r.package_registry,
            vuln_title=r.vuln_title,
        ))

    return PuzzleListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/puzzles/{puzzle_id}", response_model=PuzzleResponse)
async def get_puzzle(puzzle_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Puzzle).where(Puzzle.id == puzzle_id))
    puzzle = result.scalar_one_or_none()
    if not puzzle:
        raise HTTPException(404, "Puzzle not found")

    vuln = await db.execute(select(Vulnerability).where(Vulnerability.id == puzzle.vulnerability_id))
    v = vuln.scalar_one()
    pkg = await db.execute(select(Package).where(Package.id == v.package_id))
    p = pkg.scalar_one()

    vote_count = (await db.execute(
        select(func.count(PuzzleVote.id)).where(PuzzleVote.puzzle_id == puzzle_id)
    )).scalar() or 0

    safe_options = [{"text": o.get("text", ""), "index": i} for i, o in enumerate(puzzle.options)]

    return PuzzleResponse(
        id=puzzle.id, vulnerability_id=puzzle.vulnerability_id,
        challenge_type=puzzle.challenge_type, title=puzzle.title,
        scenario=puzzle.scenario, options=safe_options,
        difficulty=puzzle.difficulty, created_at=puzzle.created_at,
        vote_count=vote_count,
        package_name=p.name, package_registry=p.registry,
        vuln_title=v.title,
    )


@router.post("/puzzles/{puzzle_id}/vote")
async def vote_on_puzzle(
    puzzle_id: uuid.UUID,
    vote: PuzzleVoteRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Puzzle).where(Puzzle.id == puzzle_id))
    puzzle = result.scalar_one_or_none()
    if not puzzle:
        raise HTTPException(404, "Puzzle not found")

    # Check if this session already voted
    existing = await db.execute(
        select(PuzzleVote).where(
            PuzzleVote.puzzle_id == puzzle_id,
            PuzzleVote.session_id == vote.session_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already voted on this puzzle")

    # Save vote
    pv = PuzzleVote(
        puzzle_id=puzzle_id,
        selected_index=vote.selected_index,
        confidence=vote.confidence,
        time_taken_secs=vote.time_taken_secs,
        session_id=vote.session_id,
    )
    db.add(pv)
    await db.commit()

    # Return results
    return await _get_results(db, puzzle, vote.selected_index)


@router.get("/puzzles/{puzzle_id}/results")
async def get_puzzle_results(
    puzzle_id: uuid.UUID,
    session_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Puzzle).where(Puzzle.id == puzzle_id))
    puzzle = result.scalar_one_or_none()
    if not puzzle:
        raise HTTPException(404, "Puzzle not found")

    # Must have voted first
    vote = await db.execute(
        select(PuzzleVote).where(
            PuzzleVote.puzzle_id == puzzle_id,
            PuzzleVote.session_id == session_id,
        )
    )
    v = vote.scalar_one_or_none()
    if not v:
        raise HTTPException(403, "Must vote before seeing results")

    return await _get_results(db, puzzle, v.selected_index)


async def _get_results(db: AsyncSession, puzzle: Puzzle, user_selection: int) -> PuzzleResultResponse:
    """Build results with consensus data."""
    votes = await db.execute(
        select(PuzzleVote).where(PuzzleVote.puzzle_id == puzzle.id)
    )
    all_votes = votes.scalars().all()

    consensus = {}
    for i in range(len(puzzle.options)):
        consensus[i] = sum(1 for v in all_votes if v.selected_index == i)

    correct_index = next(
        (i for i, o in enumerate(puzzle.options) if o.get("is_correct")),
        0
    )

    return PuzzleResultResponse(
        id=puzzle.id,
        title=puzzle.title,
        scenario=puzzle.scenario,
        options=puzzle.options,  # Full options with is_correct
        explanation=puzzle.explanation,
        consensus=consensus,
        total_votes=len(all_votes),
        user_was_correct=(user_selection == correct_index),
    )


@router.get("/puzzle-stats", response_model=PuzzleStatsResponse)
async def get_puzzle_stats(db: AsyncSession = Depends(get_db)):
    total_puzzles = (await db.execute(select(func.count(Puzzle.id)))).scalar() or 0
    total_votes = (await db.execute(select(func.count(PuzzleVote.id)))).scalar() or 0

    return PuzzleStatsResponse(
        total_puzzles=total_puzzles,
        total_votes=total_votes,
        avg_accuracy=None,  # TODO: calculate from votes vs correct answers
        consensus_rate=None,  # TODO: calculate from puzzles with >60% agreement
    )
