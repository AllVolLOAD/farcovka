<!-- 18c2d9a1-662b-4d8f-a14f-0ff8fb34f14c 0651e721-060a-4270-afce-96b706bbbba1 -->
# Дорожная карта (с учётом архитектуры v1.0 из `архитектура.txt`)

## Фаза 0 — Консолидация требований (готовим основу)

- Принять новую модель угроз/инварианты: источник истины HOT — Vault; оффчейн не может украсть; emergencyWithdraw всегда доступен; COLD независим; доход — спред (без on-chain комиссий/tiers).
- Свести архитектуру в единый MD `DeFiish_HOT_COLD_design_v1.md` по частям 1/3–3/3: принципы, threat model, high-level, роли/границы доверия, спред-модель, off-chain слой, event pipeline, runbook.
- Зафиксировать отличие: Vault не реализует on-chain fee/computeFee; монетизация — спред в backend.

## Фаза 1 — Спецификация Vault v2 + Registry (контрактная часть)

- Уточнить спецификацию Vault v2 по архитектуре v1.0: роли governance/guardian/operator с timelock, запреты adminWithdraw, emergencyWithdraw всегда включён, режимы depositsPaused/emergencyMode, storage (balances, totalAssigned, maxTVL, tokenEnabled, allowedMigrations), функции deposit/withdraw/emergencyWithdraw, migrate, pause, setOperator, allowMigration.
- Registry (опционально): каталог активных Vault по токенам/сетям.
- Определить миграцию: allowedMigrations whitelist, self-migration пользователями.
- Подготовить тест-план: happy/edge (оператор жив/пропал, emergency, pause, migrate, reentrancy, reorg idempotency на событиях), Sepolia интеграция.

## Фаза 2 — Реализация и деплой контрактов

- Реализовать Vault v2 (Solidity OZ): безопасные transfer, reentrancy guard, роли/моды, отсутствие функций, позволяющих изъять чужие средства, поддержка ERC-20.
- Реализовать Registry (если решаем использовать) и timelock/multisig wiring.
- Написать тесты (unit + fork/Sepolia сценарии) по тест-плану.
- Деплой через Hardhat/Foundry, зафиксировать адреса для backend/miniapp.

## Фаза 3 — Backend HOT (on-chain источник)

- Сделать Vault on-chain источником: user_balances как кэш; все проверки/резервы сверять с on-chain state.
- Обновить VaultListener: события Deposit/Withdraw/EmergencyWithdraw/Migrate idempotent, reconcile с подтверждениями/reorg.
- TransactionBuilder: deposit/withdraw/migrate; без on-chain fee логики (доход — спред).
- RPC-абстракция: пул провайдеров, healthcheck/fallback/retry.

## Фаза 4 — COLD non-custodial

- Стабилизировать WalletConnect v2: сессии, восстановление, смена сети, ошибки.
- Фронт: прямое чтение балансов/состояний; депозиты/выводы без зависимости от backend; emergency path для HOT.

## Фаза 5 — Governance/оператор

- Подключить multisig/timelock для governance: setOperator, pause, allowMigration, token enable/disable, maxTVL.
- Задел под DAO/on-chain voting (в будущем) для смены оператора/параметров.

## Фаза 6 — Emergency-клиент

- CLI/mini-dapp: show-balance, emergency-withdraw, show-operator/governance; работает без backend/Telegram.

## Фаза 7 — Наблюдаемость

- Метрики: баланс Vault vs totalAssigned, число emergency, расхождения on-chain/БД.
- Алерты: смена оператора, pause/unpause, рост emergency, расхождение балансов.
- Бэкапы: БД/конфиги (без приватников; ключи в HSM/смарт-карте).

## Фаза 8 — Документация

- Обновить: M1_IMPLEMENTATION.md, TEST_PLAN.md, MANUAL_TESTING_GUIDE.md, PROJECT_SUMMARY.md.
- Добавить runbook: оператор пропал, RPC упали, миграция контракта, смена governance/operator.