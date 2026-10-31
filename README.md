# St Stephen School Accounting & Financial Management System

A production-oriented school finance platform built to the approved engineering specification.

## Architecture

- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Frontend: React + TypeScript (Vite)
- Offline client: PWA + IndexedDB with explicit sync/conflict handling
- Deployment: frontend on Vercel; Django API on a Python application host; managed PostgreSQL

## Financial integrity principles

- All posted transactions use balanced double-entry journals.
- Posted records are immutable; corrections use reversals and adjusting entries.
- Financial writes are atomic and protected by database constraints.
- All sensitive actions are permission-checked and audited.
- No production financial figures or credentials are seeded into the repository.

## Project status

Repository initialized. Implementation, automated tests, security verification, infrastructure provisioning, and production deployment are not yet complete. Do not use with live school financial data until the release acceptance checklist is passed.

## Local development

See `docs/DEVELOPMENT.md` for the planned setup and `docs/IMPLEMENTATION_PLAN.md` for phased delivery.