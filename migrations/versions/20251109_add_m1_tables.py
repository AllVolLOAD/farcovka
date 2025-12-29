"""Add M1 tables: wallet_accounts, wc_sessions, orders, transactions

Revision ID: add_m1_tables
Revises: fix_pair_source_unique
Create Date: 2025-11-09 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = 'add_m1_tables'
down_revision = 'fix_pair_source_unique'
branch_labels = None
depends_on = None


def upgrade():
    # wallet_accounts table
    op.create_table('wallet_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.tg_id'), nullable=False),
        sa.Column('address', sa.String(42), nullable=False, unique=True),
        sa.Column('chain_id', sa.Integer(), default=11155111),  # Sepolia
        sa.Column('wallet_type', sa.String(20), default='external'),  # external/local/custodial
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_wallet_accounts_user_id', 'wallet_accounts', ['user_id'])
    op.create_index('ix_wallet_accounts_address', 'wallet_accounts', ['address'])
    
    # wc_sessions table
    op.create_table('wc_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('wallet_id', sa.Integer(), sa.ForeignKey('wallet_accounts.id')),
        sa.Column('topic', sa.String(128), unique=True),
        sa.Column('peer_metadata', JSON()),
        sa.Column('expiry', sa.DateTime()),
        sa.Column('status', sa.String(20), default='active'),  # active/expired/disconnected
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_wc_sessions_topic', 'wc_sessions', ['topic'])
    op.create_index('ix_wc_sessions_wallet_id', 'wc_sessions', ['wallet_id'])
    
    # orders table (заказы обмена)
    op.create_table('orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.tg_id')),
        sa.Column('wallet_id', sa.Integer(), sa.ForeignKey('wallet_accounts.id')),
        sa.Column('type', sa.String(10)),  # buy/sell
        sa.Column('currency_pair', sa.String(10)),  # USD/RUB
        sa.Column('amount_crypto', sa.Numeric(18, 8)),  # Сумма в токенах (USDT)
        sa.Column('amount_fiat', sa.Numeric(12, 2)),    # Сумма в фиате
        sa.Column('rate', sa.Numeric(10, 4)),
        sa.Column('status', sa.String(20), default='pending'),  # pending/deposit_wait/processing/completed/cancelled
        sa.Column('deposit_address', sa.String(42)),  # Адрес для депозита (если buy)
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now())
    )
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_wallet_id', 'orders', ['wallet_id'])
    
    # transactions table (история блокчейн-операций)
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('tx_hash', sa.String(66), unique=True),
        sa.Column('from_address', sa.String(42)),
        sa.Column('to_address', sa.String(42)),
        sa.Column('amount', sa.Numeric(18, 8)),
        sa.Column('chain_id', sa.Integer()),
        sa.Column('type', sa.String(20)),  # deposit/withdrawal
        sa.Column('status', sa.String(20), default='pending'),  # pending/confirmed/failed
        sa.Column('confirmations', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_transactions_hash', 'transactions', ['tx_hash'])
    op.create_index('ix_transactions_order_id', 'transactions', ['order_id'])
    op.create_index('ix_transactions_status', 'transactions', ['status'])


def downgrade():
    op.drop_table('transactions')
    op.drop_table('orders')
    op.drop_table('wc_sessions')
    op.drop_table('wallet_accounts')

