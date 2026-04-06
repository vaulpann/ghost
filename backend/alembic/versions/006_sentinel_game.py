"""Add Supply Chain Sentinel game tables

Revision ID: 006
Revises: 005
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Game scenarios — each represents a package update to inspect
    # Can be historical (from the 20 real attacks) or live (from Ghost's feed)
    op.create_table(
        'sentinel_scenarios',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source', sa.String(20), nullable=False),  # 'historical' or 'live'
        sa.Column('difficulty', sa.String(20), nullable=False),  # tutorial, easy, medium, hard, expert
        sa.Column('is_malicious', sa.Boolean(), nullable=False),  # ground truth
        sa.Column('attack_name', sa.String(200), nullable=True),  # e.g. "XZ Utils Backdoor"
        sa.Column('attack_type', sa.String(100), nullable=True),  # e.g. "maintainer_takeover"
        # Package metadata
        sa.Column('package_name', sa.String(255), nullable=False),
        sa.Column('registry', sa.String(50), nullable=False),
        sa.Column('version_from', sa.String(100), nullable=True),
        sa.Column('version_to', sa.String(100), nullable=True),
        # The 6 inspection dimensions — each is a JSON blob of visual data
        sa.Column('identity_data', postgresql.JSON(), nullable=False),     # ID Badge tool
        sa.Column('timing_data', postgresql.JSON(), nullable=False),       # Timeline Scanner tool
        sa.Column('shape_data', postgresql.JSON(), nullable=False),        # X-Ray tool
        sa.Column('behavior_data', postgresql.JSON(), nullable=False),     # Cargo Scanner tool
        sa.Column('flow_data', postgresql.JSON(), nullable=False),         # Flight Tracker tool
        sa.Column('context_data', postgresql.JSON(), nullable=False),      # Context Lens tool
        # Post-mortem (shown after verdict)
        sa.Column('postmortem', sa.Text(), nullable=True),  # Full explanation markdown
        sa.Column('real_cve', sa.String(50), nullable=True),
        sa.Column('real_cvss', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sentinel_scenarios_source', 'sentinel_scenarios', ['source'])
    op.create_index('ix_sentinel_scenarios_difficulty', 'sentinel_scenarios', ['difficulty'])

    # Player verdicts on scenarios
    op.create_table(
        'sentinel_verdicts',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('scenario_id', sa.UUID(), sa.ForeignKey('sentinel_scenarios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('verdict', sa.String(20), nullable=False),  # 'safe', 'suspicious', 'malicious'
        sa.Column('confidence', sa.Float(), nullable=False),  # 0.0-1.0
        sa.Column('attack_type_guess', sa.String(100), nullable=True),  # player's guess of attack pattern
        sa.Column('evidence_notes', postgresql.JSON(), nullable=True),  # which tools/signals they flagged
        sa.Column('time_taken_secs', sa.Float(), nullable=True),
        sa.Column('tools_used', postgresql.JSON(), nullable=True),  # which of the 6 tools they checked
        sa.Column('is_correct', sa.Boolean(), nullable=True),  # computed after submission
        sa.Column('score', sa.Integer(), nullable=True),  # points earned
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sentinel_verdicts_scenario_id', 'sentinel_verdicts', ['scenario_id'])
    op.create_index('ix_sentinel_verdicts_session_id', 'sentinel_verdicts', ['session_id'])

    # Player profiles (anonymous, session-based)
    op.create_table(
        'sentinel_players',
        sa.Column('session_id', sa.String(100), primary_key=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(50), nullable=False, server_default='Dock Worker'),
        sa.Column('total_inspections', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_flags', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('false_flags', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('missed_attacks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('best_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('detection_rate', sa.Float(), nullable=True),
        sa.Column('false_positive_rate', sa.Float(), nullable=True),
        sa.Column('vote_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('sentinel_players')
    op.drop_table('sentinel_verdicts')
    op.drop_table('sentinel_scenarios')
