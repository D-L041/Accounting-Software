# Precious SchoolBooks

School accounting and financial management platform by **DKL Accounting Services**, with **St Stephen School** as the initial school workspace.

## Product scope

A multi-school accounting platform for Kenyan primary and secondary schools. The current build provides online school operations, student records, fee billing, receipts, supplier/expense recording and double-entry ledger controls. Offline-capable PWA operation is a later release phase.

## Architecture

- Backend: Django + Django REST Framework
- Database: PostgreSQL in production
- Frontend: React + TypeScript (Vite)
- Authentication: CSRF-protected Django sessions
- Deployment target: Vercel frontend and a separately hosted Django API with managed PostgreSQL

## Implemented in the development branch

- School workspaces, memberships and role-scoped access (owner, admin, accountant, bursar, viewer).
- Academic years, classes/streams and student records.
- School-scoped chart of accounts, financial periods and journal entries.
- Balanced double-entry posting, locked-period checks and immutable posted journals/lines.
- Fee items, draft invoices, invoice issuance and automatic receivables/income journal posting.
- Cash, bank and M-Pesa receipt recording, invoice allocations and balance updates.
- Supplier directory, expense categories and draft expense entry.
- Expense posting to the appropriate expense and cash/bank/M-Pesa accounts.
- Secure sign-in/sign-out API and school-aware frontend workspace.
- Frontend forms for student, class, invoice, payment, supplier and expense workflows.
- Trial balance, income and expenditure, and balance sheet APIs and frontend reports.\n- Immutable audit events for journal posting, invoice issue, receipt recording, expense posting and financial-period locking, with a school-scoped audit-log view.

## Financial integrity principles

- Every posted journal must balance.
- Journal dates must fall inside an unlocked financial period.
- Each journal line must contain exactly one positive debit or credit.
- Posted journals, lines and posted expenses are immutable.
- Corrections must use authorised reversals or adjusting entries (workflow still to be implemented).
- Trial balance totals are calculated from posted ledger lines only.
- No production financial figures or credentials are seeded into the repository.

## Current delivery status

This is an active development build, **not yet a production-ready accounting application**. The frontend and backend are connected, but production configuration, deployment, offline sync, broader audit-event coverage, payroll, supplier bills/payables, bank reconciliation, budgets, cash flow reporting, approvals, backup/restore drills and full end-to-end acceptance testing remain outstanding. Do not use it for live school financial records until the release checklist is complete.

See:
- `docs/IMPLEMENTATION_PLAN.md` for phased delivery.
- `docs/DEVELOPMENT.md` for local setup.
- `docs/RELEASE_CHECKLIST.md` for production acceptance gates.

## Local development

Use Python 3.12+, PostgreSQL 16+ and Node.js 22+. Copy `.env.example` to `.env`, set local-only credentials, install dependencies, run migrations and execute the test suite. Never use real student or payroll data in a development environment.
