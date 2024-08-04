"""create_modems_table

Revision ID: be5b4870809f
Revises: 
Create Date: 2024-08-03 23:32:59.359880

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "be5b4870809f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "modems",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("modem_ip", sa.String(16), nullable=False),
        sa.Column("token", sa.String(32), nullable=False),
        sa.Column("bind_user", sa.String(50), nullable=False),
        sa.Column("modem_username", sa.String(20), nullable=True),
        sa.Column("modem_password", sa.String(20), nullable=True),
        sa.Column("reboot", sa.DateTime, nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("modems")
