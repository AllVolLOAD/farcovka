"""Add user_stats table

Revision ID: b172a79379f1
Revises: 
Create Date: 2025-09-26 02:14:11.361348

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'your_revision_hash'
down_revision = 'previous_revision_hash'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('user_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_stats_id'), 'user_stats', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_user_stats_id'), table_name='user_stats')
    op.drop_table('user_stats')
