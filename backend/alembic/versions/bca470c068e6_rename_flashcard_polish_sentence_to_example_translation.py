"""Rename flashcards.polish_sentence -> example_translation

Revision ID: bca470c068e6
Revises: 6a3fafbb9b13
Create Date: 2026-10-02 21:45:00.000000

The column was added in 435f7893aa06 under the name ``polish_sentence`` but
never wired to the model. Every AI prompt that produces flashcards already
returns the field as ``example_translation`` (and the lesson UI reads it under
that name), so the column follows suit - it pairs with ``example_sentence``.
The column was empty when renamed, so no data moves.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'bca470c068e6'
down_revision: Union[str, None] = '6a3fafbb9b13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('flashcards', schema=None) as batch_op:
        batch_op.alter_column('polish_sentence', new_column_name='example_translation')


def downgrade() -> None:
    with op.batch_alter_table('flashcards', schema=None) as batch_op:
        batch_op.alter_column('example_translation', new_column_name='polish_sentence')
