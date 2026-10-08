import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db import Base


def utc_now():
    return datetime.now(timezone.utc)

class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename = Column(String(255), nullable=False)
    video_path = Column(String(512), nullable=True)  # NULL for imported matches
    status = Column(String(32), nullable=False, default="uploaded")  # uploaded|queued|processing|completed|failed
    progress = Column(Integer, nullable=False, default=0)
    progress_message = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    pipeline_mode = Column(String(32), nullable=False, default="real")  # real|imported
    video_fps = Column(Float, nullable=True)
    video_width = Column(Integer, nullable=True)
    video_height = Column(Integer, nullable=True)
    video_duration_s = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    results = relationship("MatchResult", back_populates="match", uselist=False, cascade="all, delete-orphan")


class MatchResult(Base):
    __tablename__ = "match_results"

    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True)
    schema_version = Column(Integer, nullable=False, default=1)
    calibration = Column(String(64), nullable=False, default="naive")
    summary = Column(JSONB, nullable=True)
    tracks = Column(JSONB, nullable=False)
    heatmaps = Column(JSONB, nullable=False)
    possession = Column(JSONB, nullable=False)
    trajectories = Column(LargeBinary, nullable=True)  # gzip-compressed JSON

    match = relationship("Match", back_populates="results")
