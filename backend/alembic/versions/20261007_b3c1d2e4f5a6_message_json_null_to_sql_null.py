"""store missing tool calls and sources as SQL NULL instead of JSON null

Revision ID: b3c1d2e4f5a6
Revises: 7a579774ca1a
Create Date: 2026-10-07 18:30:00

Until now, user messages stored the JSON value `null` in messages.tool_calls/sources. The model now
uses JSONB(none_as_null=True); this converts existing rows so both mean the same thing.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b3c1d2e4f5a6"
down_revision: str | None = "7a579774ca1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE messages SET tool_calls = NULL WHERE tool_calls = 'null'::jsonb")
    op.execute("UPDATE messages SET sources = NULL WHERE sources = 'null'::jsonb")


def downgrade() -> None:
    pass  # SQL NULL is a valid value for both columns in the old schema as well
