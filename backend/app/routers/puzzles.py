import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.puzzle import Puzzle, PuzzleAttempt
from app.models.vulnerability import Vulnerability
from app.models.package import Package
from app.schemas.puzzle import (
    PuzzleAttemptRequest,
    PuzzleAttemptResponse,
    PuzzleListResponse,
    PuzzleResponse,
    PuzzleStatsResponse,
)

router = APIRouter(tags=["puzzles"])


@router.get("/puzzles", response_model=PuzzleListResponse)
async def list_puzzles(
    game_type: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            Puzzle.id, Puzzle.vulnerability_id, Puzzle.game_type,
            Puzzle.title, Puzzle.flavor_text, Puzzle.level_data,
            Puzzle.difficulty, Puzzle.par_time_secs, Puzzle.created_at,
            func.count(PuzzleAttempt.id).label("total_attempts"),
            func.avg(case(
                (PuzzleAttempt.solved == True, 1.0),  # noqa: E712
                else_=0.0
            )).label("solve_rate"),
            func.avg(case(
                (PuzzleAttempt.solved == True, PuzzleAttempt.time_taken_secs),  # noqa: E712
                else_=None
            )).label("avg_solve_time"),
            Package.name.label("package_name"),
            Package.registry.label("package_registry"),
        )
        .join(Vulnerability, Puzzle.vulnerability_id == Vulnerability.id)
        .join(Package, Vulnerability.package_id == Package.id)
        .outerjoin(PuzzleAttempt, PuzzleAttempt.puzzle_id == Puzzle.id)
        .group_by(Puzzle.id, Package.name, Package.registry)
    )
    count_query = select(func.count(Puzzle.id))

    if game_type:
        query = query.where(Puzzle.game_type == game_type)
        count_query = count_query.where(Puzzle.game_type == game_type)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Puzzle.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )

    items = []
    for r in result.all():
        items.append(PuzzleResponse(
            id=r.id, vulnerability_id=r.vulnerability_id,
            game_type=r.game_type, title=r.title,
            flavor_text=r.flavor_text, level_data=r.level_data,
            difficulty=r.difficulty, par_time_secs=r.par_time_secs,
            created_at=r.created_at,
            total_attempts=r.total_attempts or 0,
            solve_rate=round(r.solve_rate, 3) if r.solve_rate is not None else None,
            avg_solve_time=round(r.avg_solve_time, 1) if r.avg_solve_time else None,
            package_name=r.package_name, package_registry=r.package_registry,
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

    # Stats
    stats = await db.execute(
        select(
            func.count(PuzzleAttempt.id).label("total"),
            func.avg(case((PuzzleAttempt.solved == True, 1.0), else_=0.0)).label("solve_rate"),  # noqa: E712
            func.avg(case((PuzzleAttempt.solved == True, PuzzleAttempt.time_taken_secs), else_=None)).label("avg_time"),  # noqa: E712
        ).where(PuzzleAttempt.puzzle_id == puzzle_id)
    )
    s = stats.one()

    return PuzzleResponse(
        id=puzzle.id, vulnerability_id=puzzle.vulnerability_id,
        game_type=puzzle.game_type, title=puzzle.title,
        flavor_text=puzzle.flavor_text, level_data=puzzle.level_data,
        difficulty=puzzle.difficulty, par_time_secs=puzzle.par_time_secs,
        created_at=puzzle.created_at,
        total_attempts=s.total or 0,
        solve_rate=round(s.solve_rate, 3) if s.solve_rate is not None else None,
        avg_solve_time=round(s.avg_time, 1) if s.avg_time else None,
        package_name=p.name, package_registry=p.registry,
    )


@router.post("/puzzles/{puzzle_id}/attempt", response_model=PuzzleAttemptResponse)
async def submit_attempt(
    puzzle_id: uuid.UUID,
    req: PuzzleAttemptRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Puzzle).where(Puzzle.id == puzzle_id))
    puzzle = result.scalar_one_or_none()
    if not puzzle:
        raise HTTPException(404, "Puzzle not found")

    attempt = PuzzleAttempt(
        puzzle_id=puzzle_id,
        session_id=req.session_id,
        solved=req.solved,
        time_taken_secs=req.time_taken_secs,
        moves=req.moves,
        solution_path=req.solution_path,
    )
    db.add(attempt)
    await db.commit()

    # Get updated stats
    stats = await db.execute(
        select(
            func.count(PuzzleAttempt.id).label("total"),
            func.avg(case((PuzzleAttempt.solved == True, 1.0), else_=0.0)).label("solve_rate"),  # noqa: E712
            func.avg(case((PuzzleAttempt.solved == True, PuzzleAttempt.time_taken_secs), else_=None)).label("avg_time"),  # noqa: E712
        ).where(PuzzleAttempt.puzzle_id == puzzle_id)
    )
    s = stats.one()

    # Rank if solved
    your_rank = None
    if req.solved and req.time_taken_secs:
        rank_result = await db.execute(
            select(func.count(PuzzleAttempt.id)).where(
                PuzzleAttempt.puzzle_id == puzzle_id,
                PuzzleAttempt.solved == True,  # noqa: E712
                PuzzleAttempt.time_taken_secs < req.time_taken_secs,
            )
        )
        your_rank = (rank_result.scalar() or 0) + 1

    return PuzzleAttemptResponse(
        id=attempt.id, puzzle_id=puzzle_id,
        solved=req.solved, time_taken_secs=req.time_taken_secs,
        moves=req.moves, created_at=attempt.created_at,
        total_attempts=s.total or 0,
        solve_rate=round(s.solve_rate, 3) if s.solve_rate is not None else 0.0,
        avg_solve_time=round(s.avg_time, 1) if s.avg_time else None,
        your_rank=your_rank,
    )


@router.get("/puzzle-stats", response_model=PuzzleStatsResponse)
async def get_puzzle_stats(db: AsyncSession = Depends(get_db)):
    total_puzzles = (await db.execute(select(func.count(Puzzle.id)))).scalar() or 0
    total_attempts = (await db.execute(select(func.count(PuzzleAttempt.id)))).scalar() or 0
    total_solves = (await db.execute(
        select(func.count(PuzzleAttempt.id)).where(PuzzleAttempt.solved == True)  # noqa: E712
    )).scalar() or 0

    solve_rate = total_solves / total_attempts if total_attempts > 0 else None

    # Breakdown by game type
    breakdown_result = await db.execute(
        select(
            Puzzle.game_type,
            func.count(func.distinct(Puzzle.id)).label("puzzles"),
            func.count(PuzzleAttempt.id).label("attempts"),
            func.sum(case((PuzzleAttempt.solved == True, 1), else_=0)).label("solves"),  # noqa: E712
        )
        .outerjoin(PuzzleAttempt, PuzzleAttempt.puzzle_id == Puzzle.id)
        .group_by(Puzzle.game_type)
    )
    breakdown = {}
    for row in breakdown_result.all():
        attempts = row.attempts or 0
        solves = row.solves or 0
        breakdown[row.game_type] = {
            "puzzles": row.puzzles,
            "attempts": attempts,
            "solves": solves,
            "solve_rate": round(solves / attempts, 3) if attempts > 0 else None,
        }

    return PuzzleStatsResponse(
        total_puzzles=total_puzzles,
        total_attempts=total_attempts,
        total_solves=total_solves,
        overall_solve_rate=round(solve_rate, 3) if solve_rate is not None else None,
        game_type_breakdown=breakdown,
    )
