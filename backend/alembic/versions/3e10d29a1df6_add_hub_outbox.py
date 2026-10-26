"""add hub_outbox

Revision ID: 3e10d29a1df6
Revises: d7f2b3c4e508
Create Date: 2026-10-26 20:56:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e10d29a1df6'
down_revision: Union[str, None] = 'd7f2b3c4e508'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only adds a table: events waiting for System-Glowny (services/hub_events.py).
    op.create_table('hub_outbox',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('payload', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.String(), nullable=True),
    sa.Column('done_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('hub_outbox', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_hub_outbox_done_at'), ['done_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_hub_outbox_id'), ['id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('hub_outbox', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_hub_outbox_id'))
        batch_op.drop_index(batch_op.f('ix_hub_outbox_done_at'))

    op.drop_table('hub_outbox')
