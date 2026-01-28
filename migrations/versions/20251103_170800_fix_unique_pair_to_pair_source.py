"""Fix unique on pair -> unique on (pair, source)

Revision ID: fix_pair_source_unique
Revises: add_source_field
Create Date: 2025-11-03 17:08:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_pair_source_unique'
down_revision = 'add_source_field'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old unique constraint on pair if present
    op.execute("ALTER TABLE exchange_rates DROP CONSTRAINT IF EXISTS exchange_rates_pair_key;")
    # Drop old simple index if present
    op.execute("DROP INDEX IF EXISTS ix_exchange_rates_pair;")
    # Ensure composite unique index exists
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_exchange_rates_pair_source ON exchange_rates (pair, source);")


def downgrade():
    # Drop composite unique index
    op.execute("DROP INDEX IF EXISTS ix_exchange_rates_pair_source;")
    # Recreate simple unique constraint on pair
    op.execute("ALTER TABLE exchange_rates ADD CONSTRAINT exchange_rates_pair_key UNIQUE (pair);")


