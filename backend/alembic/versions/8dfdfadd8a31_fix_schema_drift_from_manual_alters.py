"""fix_schema_drift_from_manual_alters

Closes the drift found by ACTION_PLAN.md F1-1 (`alembic check` against the
live DB): historical manual ad-hoc changes and removed features left the
schema out of sync with the SQLAlchemy models.

- flashcards.gesture_anchor / spatial_anchor: leftover columns from a
  retracted kinaesthetic-anchor feature, no longer referenced anywhere in
  the codebase (verified via grep before writing this migration). These
  predate `ff1cf77eb17f_baseline_schema` (which never declared them), so
  they only exist on the live pre-Alembic DB, not on a fresh install.
- users.neuro_weights: leftover column from the retracted "neuro-wagi"
  feature (see docs/API_FUNCTIONS.md 2026-08-07 audit entry), likewise
  unreferenced and likewise absent from a fresh install.
- users.login_token unique constraint: `ff1cf77eb17f_baseline_schema`
  already declares this at table-creation time, so a fresh install already
  has it — only the live DB (created via `create_all()` before Alembic
  existed, then `stamp head`-ed straight onto the baseline without actually
  running it) is missing it. Verified no duplicate non-null values exist
  before adding it.
- flashcards.is_mastered / last_review_date / last_recall_date: the
  baseline migration already declares these exactly as the models do
  (nullable Boolean, DateTime) — the `alter_column` calls below are true
  no-ops on a fresh install and only have an effect on the live DB, where
  `is_mastered` was still NOT NULL and the datetime columns were TIMESTAMP
  (a cosmetic SQLite type-affinity difference; harmless either way).
topics.parent_id and its index/FK are handled separately in the next
revision (9c1a1e9b7b4f_add_topics_hierarchy_and_mnemonic) — that column
doesn't exist yet at this point on a fresh install, so an index on it
can't be created here.

The drop_column / create_unique_constraint calls are guarded by an
inspector check so this migration is idempotent-safe on a fresh
`alembic upgrade head` install (no gesture_anchor/spatial_anchor/
neuro_weights/login_token-constraint to touch there) as well as on the
live pre-Alembic DB (which has all of them to fix).

Revision ID: 8dfdfadd8a31
Revises: 5a6d111e51d9
Create Date: 2026-08-19 01:46:59.435723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8dfdfadd8a31'
down_revision: Union[str, None] = '5a6d111e51d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table_name):
    return {c["name"] for c in inspector.get_columns(table_name)}


def _unique_constraint_names(inspector, table_name):
    names = {uc["name"] for uc in inspector.get_unique_constraints(table_name) if uc["name"]}
    # SQLite may also expose a unique constraint as a unique index.
    names |= {ix["name"] for ix in inspector.get_indexes(table_name) if ix.get("unique")}
    return names


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    flashcards_cols = _columns(inspector, "flashcards")
    users_cols = _columns(inspector, "users")
    users_unique = _unique_constraint_names(inspector, "users")

    with op.batch_alter_table('flashcards', schema=None) as batch_op:
        batch_op.alter_column('last_review_date',
               existing_type=sa.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True)
        batch_op.alter_column('last_recall_date',
               existing_type=sa.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True)
        batch_op.alter_column('is_mastered',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('0'))
        if 'spatial_anchor' in flashcards_cols:
            batch_op.drop_column('spatial_anchor')
        if 'gesture_anchor' in flashcards_cols:
            batch_op.drop_column('gesture_anchor')

    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'uq_users_login_token' not in users_unique and 'login_token' not in users_unique:
            batch_op.create_unique_constraint('uq_users_login_token', ['login_token'])
        if 'neuro_weights' in users_cols:
            batch_op.drop_column('neuro_weights')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    users_cols = _columns(inspector, "users")
    flashcards_cols = _columns(inspector, "flashcards")
    users_unique = _unique_constraint_names(inspector, "users")

    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'neuro_weights' not in users_cols:
            batch_op.add_column(sa.Column('neuro_weights', sa.TEXT(), server_default=sa.text('\'{"sleep_modulator_weight": 0.15, "time_of_day_weight": 0.1, "interleaving_bonus_weight": 0.05, "interference_penalty_weight": 0.1}\''), nullable=True))
        if 'uq_users_login_token' in users_unique:
            batch_op.drop_constraint('uq_users_login_token', type_='unique')

    with op.batch_alter_table('flashcards', schema=None) as batch_op:
        if 'gesture_anchor' not in flashcards_cols:
            batch_op.add_column(sa.Column('gesture_anchor', sa.VARCHAR(), nullable=True))
        if 'spatial_anchor' not in flashcards_cols:
            batch_op.add_column(sa.Column('spatial_anchor', sa.VARCHAR(), nullable=True))
        batch_op.alter_column('is_mastered',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('0'))
        batch_op.alter_column('last_recall_date',
               existing_type=sa.DateTime(),
               type_=sa.TIMESTAMP(),
               existing_nullable=True)
        batch_op.alter_column('last_review_date',
               existing_type=sa.DateTime(),
               type_=sa.TIMESTAMP(),
               existing_nullable=True)
