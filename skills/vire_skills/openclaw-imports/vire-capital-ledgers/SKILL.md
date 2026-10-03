---
name: vire-capital-ledgers
description: "Use when designing a manual SQLite ledger with clear separation from any paper-trading experiment."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, sqlite, governance, paper-trading, safety]
    related_skills: [vire]
---

# Vire — Manual Capital Ledgers

Track real-world deposits, expenses, balances, and snapshots separately from simulations or trading systems.

**Safety boundaries:** manual-only; no live bank connections; never store debit-card/account/routing numbers or trading credentials.

## Structure

**SQLite tables:** `capital_accounts`, `capital_transactions`, `capital_snapshots`

**Ledger CLI actions:** `--init`, `--create-account`, `--deposit`, `--expense`, `--snapshot`, `--report`

## Governance report

Always include safety status (live-trading enabled/disabled, bank connection status), manual-ledger balance, paper balance, PnL, risk state, and recommended next action.

## Paper-trial safety guardrails

- Keep simulations clearly labeled and disconnected from live trading or bank credentials.
- Require the operator to set risk limits for their own experiment; do not inherit another deployment's numbers.
- Never convert a paper action into a live order without explicit authorization.

## External market data feed safety

Accept only configured watchlist symbols; validate `high >= low`, positive prices, 60+ trading days; preserve source truth in reports; mock is final fallback only.
