"""compatibility bridge for historical identity migration

Revision ID: 0004_identity_subscription_chat_upgrade
Revises: 0005_locked_identity_subscription_documents

This revision originally existed as a competing branch from 0003 and duplicated
schema work now represented by 0004_add_paystack_and_chat + 0005. It is kept as
a no-op compatibility revision so deployments that already recorded this
revision can continue forward without an unknown revision, while fresh installs
have one linear migration graph.
"""

revision = "0004_identity_subscription_chat_upgrade"
down_revision = "0005_locked_identity_subscription_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
