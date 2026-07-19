"""locked identity subscription documents upgrade

Revision ID: 0005_locked_identity_subscription_documents
Revises: 0004_add_paystack_and_chat
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_locked_identity_subscription_documents"
down_revision = "0004_add_paystack_and_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("user_type", sa.String(length=64), nullable=False, server_default="CUSTOMER"))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_user_type", "users", ["user_type"])

    op.add_column("agent_profiles", sa.Column("user_type", sa.String(length=64), nullable=False, server_default="BUSINESS_AGENT"))
    op.add_column("agent_profiles", sa.Column("operating_mode", sa.String(length=32), nullable=False, server_default="NOXER_MANAGED"))
    op.add_column("agent_profiles", sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="INACTIVE"))
    op.add_column("agent_profiles", sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_profiles", sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_profiles", sa.Column("last_subscription_transaction_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_agent_profiles_user_type", "agent_profiles", ["user_type"])
    op.create_index("ix_agent_profiles_operating_mode", "agent_profiles", ["operating_mode"])
    op.create_index("ix_agent_profiles_subscription_status", "agent_profiles", ["subscription_status"])
    op.create_index("ix_agent_profiles_subscription_expires_at", "agent_profiles", ["subscription_expires_at"])

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("otp_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_ip", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_email_verification_tokens_user_id_users"),
        sa.UniqueConstraint("token_hash", name="uq_email_verification_tokens_token_hash"),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])
    op.create_index("ix_email_verification_tokens_token_hash", "email_verification_tokens", ["token_hash"])
    op.create_index("ix_email_verification_tokens_otp_hash", "email_verification_tokens", ["otp_hash"])
    op.create_index("ix_email_verification_tokens_expires_at", "email_verification_tokens", ["expires_at"])

    op.create_table(
        "user_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("document_number", sa.String(length=120), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_documents_user_id_users"),
        sa.ForeignKeyConstraint(["agent_profile_id"], ["agent_profiles.id"], ondelete="CASCADE", name="fk_user_documents_agent_profile_id_agent_profiles"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], name="fk_user_documents_reviewed_by_id_users"),
        sa.UniqueConstraint("agent_profile_id", "document_type", name="uq_user_documents_agent_document_type"),
    )
    op.create_index("ix_user_documents_user_id", "user_documents", ["user_id"])
    op.create_index("ix_user_documents_agent_profile_id", "user_documents", ["agent_profile_id"])
    op.create_index("ix_user_documents_document_type", "user_documents", ["document_type"])
    op.create_index("ix_user_documents_status", "user_documents", ["status"])

    op.add_column("transactions", sa.Column("subscription_duration_months", sa.Integer(), nullable=False, server_default="12"))
    op.add_column("transactions", sa.Column("subscription_period_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("transactions", sa.Column("subscription_period_end", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("transactions", "payment_type", server_default="AGENT_SUBSCRIPTION", existing_type=sa.String(length=60), existing_nullable=False)

    op.add_column("chats", sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("chats", sa.Column("underlying_agent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("chats", sa.Column("routed_through_noxer", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("chats", sa.Column("visible_contact_type", sa.String(length=32), nullable=False, server_default="AGENT"))
    op.create_index("ix_chats_target_user_id", "chats", ["target_user_id"])
    op.create_index("ix_chats_underlying_agent_id", "chats", ["underlying_agent_id"])
    op.create_foreign_key("fk_chats_target_user_id_users", "chats", "users", ["target_user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_chats_underlying_agent_id_agent_profiles", "chats", "agent_profiles", ["underlying_agent_id"], ["id"], ondelete="SET NULL")

    op.add_column("messages", sa.Column("client_message_id", sa.String(length=120), nullable=True))
    op.create_index("ix_messages_client_message_id", "messages", ["client_message_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_client_message_id", table_name="messages")
    op.drop_column("messages", "client_message_id")
    op.drop_constraint("fk_chats_underlying_agent_id_agent_profiles", "chats", type_="foreignkey")
    op.drop_constraint("fk_chats_target_user_id_users", "chats", type_="foreignkey")
    op.drop_index("ix_chats_underlying_agent_id", table_name="chats")
    op.drop_index("ix_chats_target_user_id", table_name="chats")
    op.drop_column("chats", "visible_contact_type")
    op.drop_column("chats", "routed_through_noxer")
    op.drop_column("chats", "underlying_agent_id")
    op.drop_column("chats", "target_user_id")
    op.alter_column("transactions", "payment_type", server_default="AGENT_VERIFICATION", existing_type=sa.String(length=60), existing_nullable=False)
    op.drop_column("transactions", "subscription_period_end")
    op.drop_column("transactions", "subscription_period_start")
    op.drop_column("transactions", "subscription_duration_months")
    op.drop_table("user_documents")
    op.drop_table("email_verification_tokens")
    op.drop_index("ix_agent_profiles_subscription_expires_at", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_subscription_status", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_operating_mode", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_user_type", table_name="agent_profiles")
    op.drop_column("agent_profiles", "last_subscription_transaction_id")
    op.drop_column("agent_profiles", "subscription_expires_at")
    op.drop_column("agent_profiles", "subscription_started_at")
    op.drop_column("agent_profiles", "subscription_status")
    op.drop_column("agent_profiles", "operating_mode")
    op.drop_column("agent_profiles", "user_type")
    op.drop_index("ix_users_user_type", table_name="users")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "user_type")
