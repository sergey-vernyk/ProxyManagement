"""alter_columns_updated_rebooted_modems_table

Revision ID: 456d541c9f25
Revises: faf6fcb1e17f
Create Date: 2024-08-07 15:38:40.162549

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import func

# revision identifiers, used by Alembic.
revision: str = "456d541c9f25"
down_revision: Union[str, None] = "faf6fcb1e17f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "modems",
        "rebooted",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )

    op.alter_column(
        "modems",
        "updated",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "modems",
        "rebooted",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    op.alter_column(
        "modems",
        "updated",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )
