"""add_tables_users_and_modems

Revision ID: 758b43696319
Revises: 
Create Date: 2024-08-04 13:47:06.908826

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "758b43696319"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=50), nullable=False),
        sa.Column("login", sa.String(length=20), nullable=False),
        sa.Column("password", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "modems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("modem_ip", sa.String(length=16), nullable=False),
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column("bind_user_id", sa.Integer(), nullable=True),
        sa.Column("modem_username", sa.String(length=20), nullable=True),
        sa.Column("modem_password", sa.String(length=20), nullable=True),
        sa.Column("reboot", sa.DateTime(), nullable=True),
        sa.Column("create", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["bind_user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("modems")
    op.drop_table("users")
