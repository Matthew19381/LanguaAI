"""add_topics_hierarchy_and_mnemonic

More drift closed for ACTION_PLAN.md F1-2, this time in the other
direction from 8dfdfadd8a31: columns that exist on the live DB (added
over time by `backend/main.py`'s ad-hoc `_migrations` startup list —
see that list for the full historical record) but were never captured
by any Alembic revision, so a *fresh* `alembic upgrade head` install
would not have them at all.

- flashcards.mnemonic (SCI-13 keyword-mnemonic feature).
- topics.parent_id + its FK + its index (topic hierarchy, used by the
  planned Bank wiedzy rebuild, docs/BACKLOG_UX_2026-08.md P2-4). The live
  DB already has the column and an inline FK (SQLite honored the
  `REFERENCES` clause in the ad-hoc `ALTER TABLE`) but never got the
  index the model declares (`index=True` on `Topic.parent_id`) — confirmed
  via `PRAGMA index_list`/`PRAGMA foreign_key_list` before writing this.

Every operation below is guarded by an inspector check so this is a
no-op for whatever the live DB already has (just adds the missing index)
and fully additive for a fresh install (adds column, FK, and index).

Revision ID: 9c1a1e9b7b4f
Revises: 8dfdfadd8a31
Create Date: 2026-08-19 02:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1a1e9b7b4f'
down_revision: Union[str, None] = '8dfdfadd8a31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table_name):
    return {c["name"] for c in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    flashcards_cols = _columns(inspector, "flashcards")
    if 'mnemonic' not in flashcards_cols:
        with op.batch_alter_table('flashcards', schema=None) as batch_op:
            batch_op.add_column(sa.Column('mnemonic', sa.Text(), nullable=True))

    topics_cols = _columns(inspector, "topics")
    topics_fks = {fk["name"] for fk in inspector.get_foreign_keys("topics") if fk["name"]}
    topics_indexes = {ix["name"] for ix in inspector.get_indexes("topics")}
    has_parent_fk = any(
        fk["referred_table"] == "topics" and fk["constrained_columns"] == ["parent_id"]
        for fk in inspector.get_foreign_keys("topics")
    )

    with op.batch_alter_table('topics', schema=None) as batch_op:
        if 'parent_id' not in topics_cols:
            batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        if not has_parent_fk:
            batch_op.create_foreign_key('fk_topics_parent_id_topics', 'topics', ['parent_id'], ['id'])
        if 'ix_topics_parent_id' not in topics_indexes:
            batch_op.create_index(batch_op.f('ix_topics_parent_id'), ['parent_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    topics_indexes = {ix["name"] for ix in inspector.get_indexes("topics")}
    has_parent_fk = any(
        fk["referred_table"] == "topics" and fk["constrained_columns"] == ["parent_id"]
        for fk in inspector.get_foreign_keys("topics")
    )

    with op.batch_alter_table('topics', schema=None) as batch_op:
        if 'ix_topics_parent_id' in topics_indexes:
            batch_op.drop_index(batch_op.f('ix_topics_parent_id'))
        if has_parent_fk:
            batch_op.drop_constraint('fk_topics_parent_id_topics', type_='foreignkey')
        batch_op.drop_column('parent_id')

    with op.batch_alter_table('flashcards', schema=None) as batch_op:
        batch_op.drop_column('mnemonic')
