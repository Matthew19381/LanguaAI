"""add topics.skill_id (Bank wiedzy entries per curriculum skill)

Revision ID: d7f2b3c4e508
Revises: c6e1a2b3d406
Create Date: 2026-10-21 15:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7f2b3c4e508'
down_revision: Union[str, None] = 'c6e1a2b3d406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only adds a nullable column; entries are created by services/knowledge.py
    # the first time the Bank wiedzy is opened.
    with op.batch_alter_table('topics', schema=None) as batch_op:
        batch_op.add_column(sa.Column('skill_id', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_topics_skill_id'), ['skill_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('topics', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_topics_skill_id'))
        batch_op.drop_column('skill_id')
