# Implementation plan

1. Foundation: school-scoped authentication and role permissions, school tenancy, financial periods, chart of accounts, immutable double-entry ledger, trial balance and immutable audit events for core financial postings are implemented. Remaining: broader CRUD audit coverage, delegated user administration and controlled reversals.
2. School operations and billing: student/class/academic-year records, fee items, draft invoices, invoice issue, cash/bank/M-Pesa receipts and payment allocations are implemented in the API and connected frontend. Remaining: fee schedules by class/term, bulk invoicing, credit notes/refunds, printable receipts and verified payment-provider callbacks.
3. Cash management: supplier directory, expense categories and draft expense recording are implemented. Posting an expense creates a balanced Dr Expense / Cr Cash, Bank or M-Pesa Clearing journal and makes the posted record immutable. Remaining: supplier bills/payables, approvals, petty cash controls, cashbook views, bank imports and reconciliation.
4. Advanced finance: payroll with effective-dated Kenyan statutory parameters, budgets, procurement, budgets, cash flow reporting and management reports.
5. Client: responsive React/TypeScript frontend, secure login, school-aware data views and forms for students, classes, fees, receipts, suppliers and expenses are implemented. Remaining: full UI coverage, accessibility/E2E tests, PWA installability, IndexedDB queue and conflict-aware offline sync.
6. Assurance: unit/integration/E2E tests, permission and tenant-isolation tests, independent security review, restore drill and production smoke tests.
7. Deployment: managed PostgreSQL, Django API hosting, Vercel frontend, DNS/HTTPS, backups, monitoring and administrator handover.

No real school records, payroll figures, statutory rates or production credentials are to be invented. Production release requires independent verification of all acceptance criteria.
