# Precious SchoolBooks

School accounting and financial management platform by **DKL Accounting Services**, with **St Stephen School** as the initial acceptance-test workspace.

## Product scope

A multi-school accounting platform for Kenyan primary and secondary schools. The development branch connects a React frontend to a Django API and PostgreSQL, with school-scoped access, billing, receipts, supplier payables, ledger reports and payroll workflows.

## Architecture

- Backend: Django + Django REST Framework
- Database: PostgreSQL in production
- Frontend: React + TypeScript (Vite)
- Authentication: CSRF-protected Django sessions
- Deployment target: Vercel frontend and a separately hosted Django API with managed PostgreSQL
- PWA: installable application shell; authenticated financial records are not cached offline

## Implemented in the development branch

- School workspaces, role-scoped access (owner, admin, accountant, bursar, viewer) and owner/admin-managed staff logins.
- Academic years, classes/streams and student records.
- School-scoped chart of accounts, financial periods and journal entries.
- Balanced double-entry posting, locked-period checks and immutable posted journals/lines.
- Fee items, class/term fee schedules, duplicate-safe bulk draft invoice generation, invoice issuance and automatic receivables/income journal posting.
- Cash, bank and M-Pesa receipt recording, invoice allocations, balance updates and downloadable PDF receipts.
- Supplier directory, expense categories, draft expenses and ledger-posted expense workflows.
- Supplier bills, owner/admin approval separation, payables posting and partial/full settlement.
- Category budgets, budget-versus-actual and variance monitoring.
- Bank statement capture, manual ledger matching, reconciliation checks and audit trail.
- Trial balance, income/expenditure, balance sheet, cashbook and cash-flow movement reports. Cash-flow opening balances are derived from prior posted ledger entries; the report is not yet a fully classified cash-flow statement.
- Credit notes and payment refunds with invoice balance adjustments and ledger reversals.
- Core payroll employee records, effective-dated statutory rules, draft payroll calculation and ledger posting.
- Daraja STK Push with persisted attempts and callback verification; C2B confirmations are captured for human statement matching and manual reconciliation.
- Immutable audit events for core financial posting actions and a school-scoped audit-log view.
- PWA manifest and service worker for the static application shell.

## Financial integrity principles

- Every posted journal must balance.
- Journal dates must fall inside an unlocked financial period.
- Each journal line must contain exactly one positive debit or credit.
- Posted journals, lines and posted expenses are immutable.
- Corrections use authorised credit notes, refunds or adjusting/reversal workflows where supported.
- Trial balance totals are calculated from posted ledger lines only.
- No production financial figures or credentials are seeded into the repository.
- Offline operation never posts financial transactions; all financial writes require an authenticated online connection.

## Current delivery status

This is an active development build, **not a production-ready accounting application**. The latest delivery includes a correction to NSSF deductibility in PAYE calculations and expanded cash-flow opening-balance reporting, but the complete payroll module still needs employee-declared reliefs, exemptions, non-cash benefits, NITA levy, statutory exports and independent practitioner sign-off.

Purchase orders and configurable supplier approval limits are not yet implemented. Full offline synchronisation and conflict resolution are not implemented; only the static app shell is available offline. Daraja sandbox end-to-end testing, school-specific Paybill mapping and unattended C2B transaction-status verification remain outstanding. Independent security testing, a witnessed backup restore, production hosting/domain configuration and St Stephen School acceptance sign-off are also required.

**Do not use live school financial or pupil records until every applicable release gate is complete.** See `docs/RELEASE_CHECKLIST.md`.

## Delivery and operations documents

- `docs/IMPLEMENTATION_PLAN.md` — phased delivery status.
- `docs/DEVELOPMENT.md` — local setup.
- `docs/RELEASE_CHECKLIST.md` — production acceptance gates.
- `docs/USER_GUIDE.md` — school administrator workflows.
- `docs/PAYROLL_STATUTORY_REVIEW.md` — Kenyan payroll statutory review and gaps.
- `docs/OFFLINE_SYNC_DESIGN.md` — safe offline draft-sync boundary.
- `docs/BACKUP_RESTORE_RUNBOOK.md` — PostgreSQL backup and restore procedure.

## Local development

Use Python 3.12+, PostgreSQL 16+ and Node.js 22+. Copy `.env.example` to `.env`, set local-only credentials, install dependencies, run migrations and execute the test suite. Never use real student or payroll data in a development environment.
