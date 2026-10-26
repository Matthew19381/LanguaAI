"""add mock_exams

Revision ID: 5b2c8e7f1a03
Revises: 3e10d29a1df6
Create Date: 2026-10-26 22:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b2c8e7f1a03'
down_revision: Union[str, None] = '3e10d29a1df6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only adds a table: mock Goethe B1 Sprechen attempts (services/mock_exam.py).
    op.create_table('mock_exams',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('scored_at', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('tasks', sa.Text(), nullable=False),
    sa.Column('teil1_history', sa.Text(), nullable=False),
    sa.Column('teil2_topic', sa.Integer(), nullable=True),
    sa.Column('teil2_transcript', sa.Text(), nullable=True),
    sa.Column('teil3', sa.Text(), nullable=True),
    sa.Column('scores', sa.Text(), nullable=True),
    sa.Column('points', sa.Float(), nullable=True),
    sa.Column('max_points', sa.Integer(), nullable=True),
    sa.Column('percent', sa.Float(), nullable=True),
    sa.Column('passed', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('mock_exams', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mock_exams_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_mock_exams_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('mock_exams', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mock_exams_user_id'))
        batch_op.drop_index(batch_op.f('ix_mock_exams_id'))

    op.drop_table('mock_exams')
