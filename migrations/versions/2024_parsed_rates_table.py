"""add parsed rates table

Revision ID: parsed_rates_table
Revises: b172a79379f1
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'parsed_rates_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('parsed_rates',
        sa.Column('source', sa.String(50), nullable=True, server_default='rapira')
    )


def downgrade():
    op.drop_table('parsed_rates')