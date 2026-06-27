"""add self_healing tables

Revision ID: 20260627_self_healing
Revises: 20260623_waitlist, notification_001
Create Date: 2026-06-27 10:00:00.000000

Creates the self-healing tables: selectors, sessions and results. Also acts as
a merge point for the previously divergent heads (main chain + notification_001).
See docs/superpowers/specs/2026-06-27-self-healing-backend-design.md
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260627_self_healing"
# Merge all divergent heads (cron branch, main waitlist chain, and the
# standalone notification root) so `alembic upgrade head` resolves to one head.
down_revision = ("20260623_waitlist", "notification_001", "9f98fb39edff")
branch_labels = None
depends_on = None


def upgrade():
    """Create self_healing_selectors, self_healing_sessions, self_healing_results."""
    # Selectors
    op.create_table(
        "self_healing_selectors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("selector_type", sa.String(), nullable=False, server_default="css"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column(
            "confidence_level",
            sa.String(),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_self_healing_selectors_id", "self_healing_selectors", ["id"])
    op.create_index("ix_self_healing_selectors_value", "self_healing_selectors", ["value"])
    op.create_index(
        "ix_self_healing_selectors_selector_type",
        "self_healing_selectors",
        ["selector_type"],
    )

    # Sessions
    op.create_table(
        "self_healing_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("total_selectors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_heals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_heals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("average_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_self_healing_sessions_id", "self_healing_sessions", ["id"])
    op.create_index("ix_self_healing_sessions_status", "self_healing_sessions", ["status"])

    # Results
    op.create_table(
        "self_healing_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("self_healing_sessions.id"),
            nullable=True,
        ),
        sa.Column(
            "selector_id",
            sa.Integer(),
            sa.ForeignKey("self_healing_selectors.id"),
            nullable=True,
        ),
        sa.Column("original_selector_value", sa.String(), nullable=False),
        sa.Column("healed_selector_value", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="success"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence_level", sa.String(), nullable=False, server_default="low"),
        sa.Column("healing_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_self_healing_results_id", "self_healing_results", ["id"])
    op.create_index(
        "ix_self_healing_results_session_id",
        "self_healing_results",
        ["session_id"],
    )
    op.create_index(
        "ix_self_healing_results_selector_id",
        "self_healing_results",
        ["selector_id"],
    )


def downgrade():
    """Drop self-healing tables."""
    op.drop_index("ix_self_healing_results_selector_id", table_name="self_healing_results")
    op.drop_index("ix_self_healing_results_session_id", table_name="self_healing_results")
    op.drop_index("ix_self_healing_results_id", table_name="self_healing_results")
    op.drop_table("self_healing_results")

    op.drop_index("ix_self_healing_sessions_status", table_name="self_healing_sessions")
    op.drop_index("ix_self_healing_sessions_id", table_name="self_healing_sessions")
    op.drop_table("self_healing_sessions")

    op.drop_index("ix_self_healing_selectors_selector_type", table_name="self_healing_selectors")
    op.drop_index("ix_self_healing_selectors_value", table_name="self_healing_selectors")
    op.drop_index("ix_self_healing_selectors_id", table_name="self_healing_selectors")
    op.drop_table("self_healing_selectors")
