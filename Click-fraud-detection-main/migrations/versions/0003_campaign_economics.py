"""Add campaign economics and an optional campaign-specific block threshold."""
import sqlalchemy as sa
from alembic import op

revision = "0003_campaign_economics"
down_revision = "0002_audit_events"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("campaigns", sa.Column("cpc", sa.Float(), nullable=False, server_default="0.50"))
    op.add_column("campaigns", sa.Column("avg_conversion_value", sa.Float(), nullable=False, server_default="25.0"))
    op.add_column("campaigns", sa.Column("expected_conversion_rate", sa.Float(), nullable=False, server_default="0.02"))
    op.add_column("campaigns", sa.Column("block_threshold", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("campaigns", "block_threshold")
    op.drop_column("campaigns", "expected_conversion_rate")
    op.drop_column("campaigns", "avg_conversion_value")
    op.drop_column("campaigns", "cpc")
