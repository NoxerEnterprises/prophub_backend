"""add paystack transactions and chat

Revision ID: 0004_add_paystack_transactions_and_chat
Revises: 0003_add_property_search_indexes
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_add_paystack_transactions_and_chat"
down_revision = "0003_add_property_search_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="PAYSTACK"),
        sa.Column("payment_type", sa.String(length=60), nullable=False, server_default="AGENT_VERIFICATION"),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="PENDING"),
        sa.Column("authorization_url", sa.Text(), nullable=True),
        sa.Column("access_code", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("provider_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_transactions_user_id_users"),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.id"], ondelete="CASCADE", name="fk_transactions_agent_id_agent_profiles"),
        sa.UniqueConstraint("reference", name="uq_transactions_reference"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_agent_id", "transactions", ["agent_id"])
    op.create_index("ix_transactions_provider", "transactions", ["provider"])
    op.create_index("ix_transactions_payment_type", "transactions", ["payment_type"])
    op.create_index("ix_transactions_reference", "transactions", ["reference"])
    op.create_index("ix_transactions_status", "transactions", ["status"])

    op.create_table(
        "chats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chat_type", sa.String(length=30), nullable=False, server_default="PRIVATE"),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("last_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL", name="fk_chats_property_id_properties"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE", name="fk_chats_created_by_id_users"),
    )
    op.create_index("ix_chats_chat_type", "chats", ["chat_type"])
    op.create_index("ix_chats_property_id", "chats", ["property_id"])
    op.create_index("ix_chats_created_by_id", "chats", ["created_by_id"])
    op.create_index("ix_chats_last_message_at", "chats", ["last_message_at"])
    op.create_index("ix_chats_property_id_created_by_id", "chats", ["property_id", "created_by_id"])

    op.create_table(
        "chat_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="MEMBER"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE", name="fk_chat_participants_chat_id_chats"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_chat_participants_user_id_users"),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_participants_chat_id_user_id"),
    )
    op.create_index("ix_chat_participants_chat_id", "chat_participants", ["chat_id"])
    op.create_index("ix_chat_participants_user_id", "chat_participants", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("message_type", sa.String(length=30), nullable=False, server_default="TEXT"),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("media_path", sa.Text(), nullable=True),
        sa.Column("media_content_type", sa.String(length=100), nullable=True),
        sa.Column("media_size_bytes", sa.Integer(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE", name="fk_messages_chat_id_chats"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE", name="fk_messages_sender_id_users"),
    )
    op.create_index("ix_messages_chat_id", "messages", ["chat_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_index("ix_messages_message_type", "messages", ["message_type"])
    op.create_index("ix_messages_deleted_at", "messages", ["deleted_at"])
    op.create_index("ix_messages_chat_id_created_at", "messages", ["chat_id", "created_at"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("chat_participants")
    op.drop_table("chats")
    op.drop_table("transactions")
