"""Add source field to exchange_rates table

Revision ID: add_source_field
Revises: b172a79379f1
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_source_field'
down_revision = 'b172a79379f1'
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем уникальный индекс на pair, так как теперь может быть несколько записей для одной пары
    # с разными источниками
    op.drop_index('ix_exchange_rates_pair', table_name='exchange_rates', if_exists=True)
    
    # Добавляем поле source
    op.add_column('exchange_rates', sa.Column('source', sa.String(), nullable=True, server_default='admin'))
    
    # Создаем составной индекс на pair и source
    op.create_index('ix_exchange_rates_pair_source', 'exchange_rates', ['pair', 'source'], unique=True)
    
    # Устанавливаем default для существующих записей
    op.execute("UPDATE exchange_rates SET source = 'admin' WHERE source IS NULL")


def downgrade():
    # Удаляем индекс
    op.drop_index('ix_exchange_rates_pair_source', table_name='exchange_rates')
    
    # Удаляем поле source
    op.drop_column('exchange_rates', 'source')
    
    # Восстанавливаем простой индекс на pair (но уже не уникальный)
    op.create_index('ix_exchange_rates_pair', 'exchange_rates', ['pair'])

