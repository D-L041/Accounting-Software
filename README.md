# Precious SchoolBooks

School accounting and financial management platform by **DKL Accounting Services**, with **St Stephen School** as the initial school workspace.

## Product scope

The approved target is a multi-school platform for Kenyan primary and secondary schools, with online operation and a planned offline-capable Progressive Web App.

## Architecture

- Backend: Django + Django REST Framework
- Database: PostgreSQL in production
- Frontend: React + TypeScript (Vite)
- Offline client: PWA + IndexedDB with explicit sync/conflict handling (not yet implemented)
- Deployment target: Vercel frontend and a separately hosted Django API with managed PostgreSQL

## Financial integrity principles

- Every posted journal must balance.
- Journal dates must fall inside an unlocked financial period.
- Each journal line must contain exactly one positive debit or credit.
- Posted journals and their lines are immutable, including bulk update/delete paths.
- Corrections must use authorised reversals or adjusting entries (workflow still to be implemented).
- Trial balance totals are calculated from posted ledger lines only.
- No production financial figures or credentials are seeded into the repository.

## Current delivery status

The repository contains the initial Django/React foundation and an in-progress ledger hardening change. This is **not yet a complete accounting application** and must not be used with live school financial data. Student fees, payment allocation, receipts, expenditure, supplier workflows, payroll, RBAC, multi-school isolation, audit-event capture, bank reconciliation, reports, offline sync, backups, deployment and release testing remain outstanding.

See:
- `docs/IMPLEMENTATION_PLAN.md` for phased delivery.
- `docs/DEVELOPMENT.md` for local setup.
- `docs/RELEASE_CHECKLIST.md` for production acceptance gates.

## Local development

Use Python 3.12+, PostgreSQL 16+ and Node.js 22+. Copy `.env.example` to `.env`, set local-only credentials, install dependencies, run migrations and execute the test suite. Never use real student or payroll data in a development environment.
