"""Add privacy-conscious audit events for IP list changes."""
import sqlalchemy as sa
from alembic import op

revision = "0002_audit_events"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_user_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(128)),
        sa.Column("metadata", sa.Text, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_audit_actor_time", "audit_events",
                    ["actor_user_id", "created_at"])


def downgrade():
    op.drop_index("idx_audit_actor_time", table_name="audit_events")
    op.drop_table("audit_events")
