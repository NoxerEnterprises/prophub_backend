"""agent access control and geographic group chats

Revision ID: 0006_agent_access_and_group_chats
Revises: 0004_identity_subscription_chat_upgrade
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_agent_access_and_group_chats"
down_revision = "0004_identity_subscription_chat_upgrade"
branch_labels = None
depends_on = None


def _columns(table: str) -> dict[str, dict]:
    return {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}


def _foreign_keys(table: str) -> set[str]:
    return {fk.get("name") for fk in sa.inspect(op.get_bind()).get_foreign_keys(table) if fk.get("name")}


def upgrade() -> None:
    # Reconcile the historical alternate 0004 branch if that revision had been
    # deployed before the migration graph was linearized.
    chat_columns = _columns("chats")
    if "title" not in chat_columns:
        op.add_column("chats", sa.Column("title", sa.String(length=200), nullable=True))
    if "last_message_id" not in chat_columns:
        op.add_column("chats", sa.Column("last_message_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "target_user_id" in chat_columns and not chat_columns["target_user_id"].get("nullable", True):
        op.alter_column("chats", "target_user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    chat_columns = _columns("chats")
    for name, column in (
        ("description", sa.Column("description", sa.Text(), nullable=True)),
        ("country", sa.Column("country", sa.String(length=100), nullable=True)),
        ("state", sa.Column("state", sa.String(length=100), nullable=True)),
        ("local_government", sa.Column("local_government", sa.String(length=120), nullable=True)),
        ("community", sa.Column("community", sa.String(length=160), nullable=True)),
        ("is_active", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"))),
    ):
        if name not in chat_columns:
            op.add_column("chats", column)

    chat_indexes = _indexes("chats")
    for name, columns in (
        ("ix_chats_country", ["country"]),
        ("ix_chats_state", ["state"]),
        ("ix_chats_local_government", ["local_government"]),
        ("ix_chats_community", ["community"]),
        ("ix_chats_is_active", ["is_active"]),
        ("ix_chats_property_id_created_by_id", ["property_id", "created_by_id"]),
        ("ix_chats_group_location", ["chat_type", "is_active", "country", "state", "local_government", "community"]),
    ):
        if name not in chat_indexes:
            op.create_index(name, "chats", columns)

    message_columns = _columns("messages")
    if "content_type" in message_columns and "media_content_type" not in message_columns:
        op.alter_column("messages", "content_type", new_column_name="media_content_type", existing_type=sa.String(length=100))
    if "file_size_bytes" in message_columns and "media_size_bytes" not in message_columns:
        op.alter_column("messages", "file_size_bytes", new_column_name="media_size_bytes", existing_type=sa.BigInteger())

    message_columns = _columns("messages")
    if "read_at" not in message_columns:
        op.add_column("messages", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    if "shared_property_id" not in message_columns:
        op.add_column("messages", sa.Column("shared_property_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_messages_shared_property_id_properties",
            "messages",
            "properties",
            ["shared_property_id"],
            ["id"],
            ondelete="SET NULL",
        )

    message_indexes = _indexes("messages")
    if "ix_messages_shared_property_id" not in message_indexes:
        op.create_index("ix_messages_shared_property_id", "messages", ["shared_property_id"])
    if "ix_messages_deleted_at" not in message_indexes:
        op.create_index("ix_messages_deleted_at", "messages", ["deleted_at"])
    if "ix_messages_chat_id_created_at" not in message_indexes:
        op.create_index("ix_messages_chat_id_created_at", "messages", ["chat_id", "created_at"])

    # The model already declares this FK; older migrations only added the column.
    if "last_subscription_transaction_id" in _columns("agent_profiles"):
        fks = _foreign_keys("agent_profiles")
        if "fk_agent_profiles_last_subscription_transaction_id_transactions" not in fks:
            op.create_foreign_key(
                "fk_agent_profiles_last_subscription_transaction_id_transactions",
                "agent_profiles",
                "transactions",
                ["last_subscription_transaction_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    fks = _foreign_keys("agent_profiles")
    if "fk_agent_profiles_last_subscription_transaction_id_transactions" in fks:
        op.drop_constraint(
            "fk_agent_profiles_last_subscription_transaction_id_transactions",
            "agent_profiles",
            type_="foreignkey",
        )

    message_indexes = _indexes("messages")
    for name in ("ix_messages_chat_id_created_at", "ix_messages_deleted_at", "ix_messages_shared_property_id"):
        if name in message_indexes:
            op.drop_index(name, table_name="messages")
    if "shared_property_id" in _columns("messages"):
        op.drop_constraint("fk_messages_shared_property_id_properties", "messages", type_="foreignkey")
        op.drop_column("messages", "shared_property_id")

    chat_indexes = _indexes("chats")
    for name in (
        "ix_chats_group_location",
        "ix_chats_is_active",
        "ix_chats_community",
        "ix_chats_local_government",
        "ix_chats_state",
        "ix_chats_country",
    ):
        if name in chat_indexes:
            op.drop_index(name, table_name="chats")

    for name in ("is_active", "community", "local_government", "state", "country", "description"):
        if name in _columns("chats"):
            op.drop_column("chats", name)
