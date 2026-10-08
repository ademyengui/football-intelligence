"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-07 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('video_path', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='uploaded'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress_message', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('pipeline_mode', sa.String(length=32), nullable=False, server_default='real'),
        sa.Column('video_fps', sa.Float(), nullable=True),
        sa.Column('video_width', sa.Integer(), nullable=True),
        sa.Column('video_height', sa.Integer(), nullable=True),
        sa.Column('video_duration_s', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        'match_results',
        sa.Column('match_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('matches.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('schema_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('calibration', sa.String(length=64), nullable=False, server_default='naive'),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tracks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('heatmaps', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('possession', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('trajectories', sa.LargeBinary(), nullable=True)
    )

def downgrade() -> None:
    op.drop_table('match_results')
    op.drop_table('matches')
