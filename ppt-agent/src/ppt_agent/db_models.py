from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    config: Mapped["ProjectConfigRecord"] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    artifacts: Mapped[list["ArtifactRecord"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectConfigRecord(Base):
    __tablename__ = "project_configs"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    scenario: Mapped[str] = mapped_column(String(64), nullable=False)
    audience: Mapped[str] = mapped_column(String(128), nullable=False)
    style_pref: Mapped[str] = mapped_column(String(64), nullable=False)
    page_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    research_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    narration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project: Mapped[ProjectRecord] = relationship(back_populates="config")


class ArtifactRecord(Base):
    __tablename__ = "artifact_records"
    __table_args__ = (
        UniqueConstraint("project_id", "artifact_type", "version", name="uq_artifact_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    project: Mapped[ProjectRecord] = relationship(back_populates="artifacts")
