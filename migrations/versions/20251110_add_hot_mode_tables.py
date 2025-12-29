"""Add HOT mode support tables and columns

Revision ID: add_hot_mode_tables
Revises: add_m1_tables
Create Date: 2025-11-10 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_hot_mode_tables'
down_revision = 'add_m1_tables'
branch_labels = None
depends_on = None


def upgrade():
    # --- users table ---
    op.add_column(
        'users',
        sa.Column(
            'hot_access_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )
    op.alter_column('users', 'hot_access_enabled', server_default=None)

    # --- orders table ---
    op.add_column(
        'orders',
        sa.Column(
            'wallet_mode',
            sa.String(length=10),
            nullable=False,
            server_default='COLD'
        )
    )
    op.execute("UPDATE orders SET wallet_mode = 'COLD' WHERE wallet_mode IS NULL;")
    op.alter_column('orders', 'wallet_mode', server_default=None)
    op.create_index('ix_orders_wallet_mode', 'orders', ['wallet_mode'])

    # --- transactions table ---
    op.add_column(
        'transactions',
        sa.Column(
            'wallet_mode',
            sa.String(length=10),
            nullable=False,
            server_default='COLD'
        )
    )
    op.execute("UPDATE transactions SET wallet_mode = 'COLD' WHERE wallet_mode IS NULL;")
    op.alter_column('transactions', 'wallet_mode', server_default=None)
    op.create_index('ix_transactions_wallet_mode', 'transactions', ['wallet_mode'])

    # --- user_balances table ---
    op.create_table(
        'user_balances',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.tg_id'), nullable=False),
        sa.Column('token', sa.String(length=10), nullable=False, server_default='USDT'),
        sa.Column('balance', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), server_onupdate=sa.func.now())
    )
    op.create_unique_constraint(
        'uq_user_balances_user_token',
        'user_balances',
        ['user_id', 'token']
    )
    op.create_index('ix_user_balances_user_id', 'user_balances', ['user_id'])
    op.create_index('ix_user_balances_token', 'user_balances', ['token'])
    op.alter_column('user_balances', 'token', server_default=None)
    op.alter_column('user_balances', 'balance', server_default=None)

    # --- hot_wallets table ---
    op.create_table(
        'hot_wallets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('address', sa.String(length=42), nullable=False, unique=True),
        sa.Column('chain_id', sa.Integer(), nullable=False, server_default='11155111'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_hot_wallets_name', 'hot_wallets', ['name'])
    op.create_index('ix_hot_wallets_chain_id', 'hot_wallets', ['chain_id'])
    op.alter_column('hot_wallets', 'chain_id', server_default=None)
    op.alter_column('hot_wallets', 'is_active', server_default=None)


def downgrade():
    # --- hot_wallets table ---
    op.drop_index('ix_hot_wallets_chain_id', table_name='hot_wallets')
    op.drop_index('ix_hot_wallets_name', table_name='hot_wallets')
    op.drop_table('hot_wallets')

    # --- user_balances table ---
    op.drop_index('ix_user_balances_token', table_name='user_balances')
    op.drop_index('ix_user_balances_user_id', table_name='user_balances')
    op.drop_constraint('uq_user_balances_user_token', 'user_balances', type_='unique')
    op.drop_table('user_balances')

    # --- transactions table ---
    op.drop_index('ix_transactions_wallet_mode', table_name='transactions')
    op.drop_column('transactions', 'wallet_mode')

    # --- orders table ---
    op.drop_index('ix_orders_wallet_mode', table_name='orders')
    op.drop_column('orders', 'wallet_mode')

    # --- users table ---
    op.drop_column('users', 'hot_access_enabled')

