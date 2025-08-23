from __future__ import annotations
# Re-export the project-wide Base to ensure a single SQLAlchemy registry shared by all models.
# This avoids multiple Base registries (which breaks relationship resolution).
from app.database import Base  # noqa: F401
