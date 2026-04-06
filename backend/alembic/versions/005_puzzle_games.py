"""Rebuild puzzles as interactive game levels

Revision ID: 005
Revises: 004
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old puzzle tables
    op.drop_table('puzzle_votes')
    op.drop_table('puzzles')

    # New game-based puzzles
    op.create_table(
        'puzzles',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vulnerability_id', sa.UUID(), sa.ForeignKey('vulnerabilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('game_type', sa.String(50), nullable=False),  # maze, parser, timing, routing, gatekeeper, factory, blueprint
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('flavor_text', sa.Text(), nullable=False),  # narrative framing, no security jargon
        sa.Column('level_data', postgresql.JSON(), nullable=False),  # game-specific level configuration
        sa.Column('difficulty', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('par_time_secs', sa.Integer(), nullable=True),  # target solve time
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_puzzles_vulnerability_id', 'puzzles', ['vulnerability_id'])
    op.create_index('ix_puzzles_game_type', 'puzzles', ['game_type'])

    # Puzzle attempts — tracks every play session
    op.create_table(
        'puzzle_attempts',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('puzzle_id', sa.UUID(), sa.ForeignKey('puzzles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('solved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('time_taken_secs', sa.Float(), nullable=True),
        sa.Column('moves', sa.Integer(), nullable=True),  # number of actions taken
        sa.Column('solution_path', postgresql.JSON(), nullable=True),  # the player's solution for analysis
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_puzzle_attempts_puzzle_id', 'puzzle_attempts', ['puzzle_id'])
    op.create_index('ix_puzzle_attempts_session_id', 'puzzle_attempts', ['session_id'])


def downgrade() -> None:
    op.drop_table('puzzle_attempts')
    op.drop_table('puzzles')
