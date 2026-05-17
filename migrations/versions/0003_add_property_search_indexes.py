"""add property search indexes

Revision ID: 0003_add_property_search_indexes
Revises: 0002_add_properties_and_media
Create Date: 2026-05-08
"""

from alembic import op

revision = "0003_add_property_search_indexes"
down_revision = "0002_add_properties_and_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_properties_search_vector
        ON properties
        USING GIN (
            to_tsvector(
                'simple',
                coalesce(title, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(country, '') || ' ' ||
                coalesce(state, '') || ' ' ||
                coalesce(local_government, '') || ' ' ||
                coalesce(community, '')
            )
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_properties_created_at ON properties (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_properties_listing_type_status ON properties (listing_type, status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_properties_listing_type_status")
    op.execute("DROP INDEX IF EXISTS ix_properties_created_at")
    op.execute("DROP INDEX IF EXISTS ix_properties_search_vector")
