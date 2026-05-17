"""add properties and property media

Revision ID: 0002_add_properties_and_media
Revises: 0001_create_async_day3_core
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_add_properties_and_media"
down_revision = "0001_create_async_day3_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
        sa.Column("country", sa.String(length=100), nullable=False, server_default="Nigeria"),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("local_government", sa.String(length=120), nullable=True),
        sa.Column("community", sa.String(length=160), nullable=True),
        sa.Column("address_details", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("listing_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="AVAILABLE"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"], ondelete="CASCADE", name="fk_properties_agent_id_agent_profiles"),
    )
    op.create_index("ix_properties_agent_id", "properties", ["agent_id"])
    op.create_index("ix_properties_title", "properties", ["title"])
    op.create_index("ix_properties_price", "properties", ["price"])
    op.create_index("ix_properties_country", "properties", ["country"])
    op.create_index("ix_properties_state", "properties", ["state"])
    op.create_index("ix_properties_local_government", "properties", ["local_government"])
    op.create_index("ix_properties_community", "properties", ["community"])
    op.create_index("ix_properties_category", "properties", ["category"])
    op.create_index("ix_properties_listing_type", "properties", ["listing_type"])
    op.create_index("ix_properties_status", "properties", ["status"])
    op.create_index("ix_properties_is_published", "properties", ["is_published"])
    op.create_index("ix_properties_deleted_at", "properties", ["deleted_at"])
    op.create_index("ix_properties_public_feed", "properties", ["is_published", "deleted_at", "status"])
    op.create_index("ix_properties_location", "properties", ["country", "state", "local_government", "community"])

    op.create_table(
        "property_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False, server_default="IMAGE"),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE", name="fk_property_media_property_id_properties"),
        sa.UniqueConstraint("property_id", "storage_path", name="uq_property_media_property_id_storage_path"),
    )
    op.create_index("ix_property_media_property_id", "property_media", ["property_id"])
    op.create_index("ix_property_media_media_type", "property_media", ["media_type"])


def downgrade() -> None:
    op.drop_table("property_media")
    op.drop_table("properties")
