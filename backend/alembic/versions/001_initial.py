"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'packages',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('registry', sa.String(20), nullable=False),
        sa.Column('registry_url', sa.Text(), nullable=True),
        sa.Column('repository_url', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('latest_known_version', sa.String(100), nullable=True),
        sa.Column('monitoring_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('weekly_downloads', sa.BigInteger(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('registry', 'name', name='uq_registry_name'),
    )
    op.create_index('ix_packages_name', 'packages', ['name'])

    op.create_table(
        'versions',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('package_id', sa.UUID(), sa.ForeignKey('packages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_string', sa.String(100), nullable=False),
        sa.Column('previous_version_string', sa.String(100), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tarball_url', sa.Text(), nullable=True),
        sa.Column('sha256_digest', sa.String(64), nullable=True),
        sa.Column('diff_size_bytes', sa.Integer(), nullable=True),
        sa.Column('diff_file_count', sa.Integer(), nullable=True),
        sa.Column('diff_content', sa.Text(), nullable=True),
        sa.Column('detection_method', sa.String(50), nullable=False, server_default='poll'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_versions_package_id', 'versions', ['package_id'])

    op.create_table(
        'analyses',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('version_id', sa.UUID(), sa.ForeignKey('versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('triage_result', postgresql.JSON(), nullable=True),
        sa.Column('triage_flagged', sa.Boolean(), nullable=True),
        sa.Column('triage_model', sa.String(50), nullable=True),
        sa.Column('triage_tokens_used', sa.Integer(), nullable=True),
        sa.Column('triage_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deep_analysis_result', postgresql.JSON(), nullable=True),
        sa.Column('deep_analysis_model', sa.String(50), nullable=True),
        sa.Column('deep_analysis_tokens_used', sa.Integer(), nullable=True),
        sa.Column('deep_analysis_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('synthesis_result', postgresql.JSON(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('risk_level', sa.String(20), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('total_cost_usd', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_analyses_status', 'analyses', ['status'])
    op.create_index('ix_analyses_risk_level', 'analyses', ['risk_level'])
    op.create_index('ix_analyses_created_at', 'analyses', ['created_at'])

    op.create_table(
        'findings',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('analysis_id', sa.UUID(), sa.ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence', postgresql.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('mitre_technique', sa.String(50), nullable=True),
        sa.Column('remediation', sa.Text(), nullable=True),
        sa.Column('false_positive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_findings_analysis_id', 'findings', ['analysis_id'])

    op.create_table(
        'alert_configs',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('channel_type', sa.String(20), nullable=False),
        sa.Column('channel_config', postgresql.JSON(), nullable=False),
        sa.Column('min_risk_level', sa.String(20), nullable=False, server_default='high'),
        sa.Column('registries', postgresql.JSON(), nullable=True),
        sa.Column('packages', postgresql.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'alert_history',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('alert_config_id', sa.UUID(), sa.ForeignKey('alert_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_id', sa.UUID(), sa.ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('response_data', postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('alert_history')
    op.drop_table('alert_configs')
    op.drop_table('findings')
    op.drop_table('analyses')
    op.drop_table('versions')
    op.drop_table('packages')
