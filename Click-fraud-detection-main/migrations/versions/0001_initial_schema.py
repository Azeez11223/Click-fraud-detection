"""Initial AdShield relational schema.

Revision ID: 0001_initial
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("campaigns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False), sa.Column("ad_type", sa.String(40), nullable=False),
        sa.Column("platform", sa.String(40), nullable=False), sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), server_default="Active"), sa.Column("api_key_hash", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("clicks_data",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("device", sa.String(40)), sa.Column("browser", sa.String(80)), sa.Column("geo_location", sa.String(100)),
        sa.Column("timestamp", sa.String(40)), sa.Column("click_interval", sa.Float), sa.Column("ip_click_count", sa.Integer),
        sa.Column("event_id", sa.String(128)),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "event_id", name="uq_clicks_data_user_event"))
    op.create_table("predictions",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("result", sa.String(20)), sa.Column("confidence", sa.Float), sa.Column("decision", sa.String(16)),
        sa.Column("reason_codes", sa.Text, server_default="[]"), sa.Column("model_version", sa.String(80)),
        sa.Column("event_id", sa.String(128)),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "event_id", name="uq_predictions_user_event"))
    op.create_table("campaign_clicks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False), sa.Column("user_agent", sa.Text, server_default=""),
        sa.Column("classification", sa.String(16), server_default="VALID", nullable=False),
        sa.Column("fraud_reason", sa.Text, server_default=""), sa.Column("score", sa.Float),
        sa.Column("decision", sa.String(16)), sa.Column("reason_codes", sa.Text, server_default="[]"),
        sa.Column("model_version", sa.String(80)), sa.Column("event_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("campaign_id", "event_id", name="uq_campaign_click_event"),
        sa.CheckConstraint("classification IN ('VALID','FRAUD','SUSPICIOUS')", name="ck_campaign_click_classification"))
    op.create_table("ip_lists",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False), sa.Column("list_type", sa.String(16), nullable=False),
        sa.Column("note", sa.Text, server_default=""), sa.Column("source", sa.String(40), server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "ip_address", name="uq_ip_lists_user_ip"),
        sa.CheckConstraint("list_type IN ('block','whitelist')", name="ck_ip_lists_type"))
    op.create_table("ip_datasets",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("row_count", sa.Integer, server_default="0"),
        sa.Column("list_type", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("list_type IN ('block','whitelist','training')", name="ck_ip_datasets_type"))
    op.create_table("ip_dataset_rows",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("dataset_id", sa.Integer, sa.ForeignKey("ip_datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False))
    op.create_table("platform_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(40), nullable=False), sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False), sa.Column("country", sa.String(100), server_default=""),
        sa.Column("device", sa.String(40), server_default=""), sa.Column("browser", sa.String(100), server_default=""),
        sa.Column("cost_usd", sa.Float, server_default="0"), sa.Column("classification", sa.String(16), server_default="VALID", nullable=False),
        sa.Column("fraud_reason", sa.Text, server_default=""), sa.Column("score", sa.Float),
        sa.Column("decision", sa.String(16)), sa.Column("reason_codes", sa.Text, server_default="[]"),
        sa.Column("model_version", sa.String(80)), sa.Column("event_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("campaign_id", "event_id", name="uq_platform_event_event"),
        sa.CheckConstraint("classification IN ('VALID','FRAUD','SUSPICIOUS')", name="ck_platform_event_classification"))
    op.create_index("idx_cc_campaign_ip_time", "campaign_clicks", ["campaign_id", "ip_address", "created_at"])
    op.create_index("idx_cc_campaign_desc", "campaign_clicks", ["campaign_id", sa.text("id DESC")])
    op.create_index("idx_pe_campaign_ip_time", "platform_events", ["campaign_id", "ip_address", "created_at"])
    op.create_index("idx_idr_dataset", "ip_dataset_rows", ["dataset_id"])
    op.create_index("idx_clicks_data_user_ip_time", "clicks_data", ["user_id", "ip_address", "created_at"])

def downgrade():
    for table in ("platform_events", "ip_dataset_rows", "ip_datasets", "ip_lists", "campaign_clicks", "predictions", "clicks_data", "campaigns", "users"):
        op.drop_table(table)
