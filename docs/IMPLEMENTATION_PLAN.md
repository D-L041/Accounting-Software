# Implementation plan

1. Foundation: configuration, authentication/RBAC, tenant boundary, audit events, financial periods, chart of accounts, immutable double-entry ledger.
2. School operations: students, classes, academic years/terms, fee structures, invoices, allocations, receipts and payment methods.
3. Cash management: supplier records, expense categories and draft expense recording are implemented. Posting an expense creates a balanced Dr Expense / Cr Cash, Bank or M-Pesa Clearing journal and makes the posted record immutable. Remaining: supplier bills/payables, approvals, petty cash controls, cashbook views, bank imports and reconciliation.
4. Advanced finance: payroll with effective-dated Kenyan statutory parameters, budgets, procurement and reports.
5. Client: React/TypeScript responsive application, accessible forms/tables, PWA caching and conflict-aware offline workflows.
6. Assurance: unit/integration/E2E tests, permission and tenant-isolation tests, security review, restore drill and production smoke tests.
7. Deployment: managed PostgreSQL, Django API hosting, Vercel frontend, DNS/HTTPS, backups and monitoring.

No real school records, payroll figures, statutory rates or production credentials are to be invented. Production release requires independent verification of all acceptance criteria.
