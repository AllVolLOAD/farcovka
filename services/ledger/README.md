# Ledger Service (Stage 1 MVP)

## Purpose
Stage 1 introduces the foundational ledger service for user accounts and balances.
This service only exposes health/readiness endpoints and a database schema for
users, accounts, transactions, and entries (double-entry ledger).

## Requirements
- Go 1.22+
- PostgreSQL

## Environment
- `DATABASE_URL` (required)
- `LEDGER_ADDR` (optional, default `:8080`)

## Run
```bash
go run ./cmd/ledger
```

## Cash desk endpoints
Create a cash deposit (pending):
```bash
curl -X POST http://localhost:8080/cash/deposits \\
  -H 'Content-Type: application/json' \\
  -d '{"user_id":"<uuid>","currency":"RUB","amount":"1000.00","note":"office cash","created_by":"cashier-1"}'
```

Confirm a cash deposit:
```bash
curl -X POST http://localhost:8080/cash/deposits/<deposit_id>/confirm \\
  -H 'Content-Type: application/json' \\
  -d '{"confirmed_by":"cashier-1","note":"verified"}'
```

## Orders (Stage 3)
Create a limit order:
```bash
curl -X POST http://localhost:8080/orders \\
  -H 'Content-Type: application/json' \\
  -d '{"user_id":"<uuid>","side":"buy","market":"RUB/USDT","price":"95.50","amount":"100.00"}'
```

Cancel an order:
```bash
curl -X POST http://localhost:8080/orders/<order_id>/cancel \\
  -H 'Content-Type: application/json' \\
  -d '{"cancelled_by":"ops-1"}'
```

Run a single match pass:
```bash
curl -X POST "http://localhost:8080/orders/match?market=RUB/USDT"
```

## Migrations
Apply the SQL migration in `migrations/001_init.sql` using your preferred tool.
