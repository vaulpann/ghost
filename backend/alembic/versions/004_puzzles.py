"""Add puzzles and puzzle_votes tables

Revision ID: 004
Revises: 003
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'puzzles',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vulnerability_id', sa.UUID(), sa.ForeignKey('vulnerabilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('challenge_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('scenario', sa.Text(), nullable=False),
        sa.Column('options', postgresql.JSON(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_puzzles_vulnerability_id', 'puzzles', ['vulnerability_id'])
    op.create_index('ix_puzzles_challenge_type', 'puzzles', ['challenge_type'])

    op.create_table(
        'puzzle_votes',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('puzzle_id', sa.UUID(), sa.ForeignKey('puzzles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('selected_index', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('time_taken_secs', sa.Float(), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_puzzle_votes_puzzle_id', 'puzzle_votes', ['puzzle_id'])
    op.create_index('ix_puzzle_votes_session_id', 'puzzle_votes', ['session_id'])


def downgrade() -> None:
    op.drop_table('puzzle_votes')
    op.drop_table('puzzles')
