"""initial baseline schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-26

This baseline applies the canonical DDL in ``db/schema.sql``. Subsequent migrations
are generated normally with Alembic autogenerate against the SQLAlchemy models.
"""
from __future__ import annotations

from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# db/schema.sql lives at <repo>/db/schema.sql — three parents up from this file:
# backend/migrations/versions/0001_initial.py -> backend/migrations/versions
_SCHEMA_SQL = (
    Path(__file__).resolve().parents[3] / "db" / "schema.sql"
)


def upgrade() -> None:
    sql = _SCHEMA_SQL.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    # Full teardown of the baseline. Drops the public schema contents and enum types.
    op.execute("DROP SCHEMA public CASCADE;")
    op.execute("CREATE SCHEMA public;")
