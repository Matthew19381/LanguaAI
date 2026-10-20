"""add skill_attempts table and exercises.skill_id

Revision ID: c6e1a2b3d406
Revises: a74c8185cae4
Create Date: 2026-10-21 02:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6e1a2b3d406'
down_revision: Union[str, None] = 'a74c8185cae4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only adds: a nullable column and a new table. Existing rows are untouched;
    # old skill tags get their ids from scripts/mapuj_umiejetnosci.py, run separately.
    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.add_column(sa.Column('skill_id', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_exercises_skill_id'), ['skill_id'], unique=False)

    op.create_table(
        'skill_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('skill_id', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('first_try', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('exercise_id', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skill_attempts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_skill_attempts_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_skill_attempts_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_skill_attempts_skill_id'), ['skill_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('skill_attempts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_skill_attempts_skill_id'))
        batch_op.drop_index(batch_op.f('ix_skill_attempts_user_id'))
        batch_op.drop_index(batch_op.f('ix_skill_attempts_id'))
    op.drop_table('skill_attempts')
    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_exercises_skill_id'))
        batch_op.drop_column('skill_id')
