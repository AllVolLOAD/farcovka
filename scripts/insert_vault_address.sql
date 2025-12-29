-- Insert VaultV2 address into hot_wallets table
-- Run this after deploying VaultV2 contract

INSERT INTO hot_wallets (name, address, chain_id, is_active, created_at)
VALUES (
    'vault',
    '0xd5523C76018FA546431D0be4DDe48f389b561C09',
    11155111,
    true,
    NOW()
)
ON CONFLICT DO NOTHING;

-- Also insert VaultRegistry if needed
-- INSERT INTO hot_wallets (name, address, chain_id, is_active, created_at)
-- VALUES (
--     'vault_registry',
--     '0xC73a812F8002FB269d2bCc5d5318233a1ecedE98',
--     11155111,
--     true,
--     NOW()
-- )
-- ON CONFLICT DO NOTHING;

