# Production release checklist

A green frontend build or successful deployment alone is not sufficient for financial-system acceptance.

## Current status

- [x] Repository and initial architecture inspected.
- [x] Ledger posting validation strengthened in the working branch.
- [x] Posted journal and line mutation paths guarded.
- [x] Production settings reject missing secrets and non-PostgreSQL databases.
- [x] Latest backend and frontend CI run observed and passed for the verified baseline (re-run required for subsequent commits).
- [x] Session authentication, role permissions, school-level tenant isolation and owner/admin staff-login management implemented and tested.
- [x] Student, class/term fee schedules, bulk draft invoicing, invoices, payment allocation and receipt workflows implemented in API and frontend.
- [x] Supplier directory, expense categories and ledger-posted expense workflow implemented.
- [ ] Payroll, budgeting, supplier bills/payables and procurement workflows implemented.
- [x] Trial balance API and frontend report implemented.
- [x] Trial balance, balance sheet and income/expenditure statements implemented.
- [x] Posted cashbook movement report implemented (period movement only; no opening balance).
- [x] API Docker image build and database health endpoint verified in CI.
- [ ] Bank reconciliation and cash flow reporting implemented.
- [x] Immutable audit events for core financial posting actions and a school-scoped audit log.
- [ ] Complete CRUD audit coverage and financial approval workflows.
- [x] Downloadable PDF receipts with school-level access checks.
- [ ] Credit note/refund and verified M-Pesa callback workflows.
- [ ] Offline data queue, sync and conflict resolution implemented and tested.
- [ ] Independent security review and expanded tenant-isolation tests passed.
- [ ] Backup schedule and a real restore drill verified.
- [ ] Production API, PostgreSQL and frontend provisioned.
- [ ] Custom domain connected and HTTPS verified.
- [ ] End-to-end accounting acceptance tests passed, including trial balance and balance sheet reconciliation.
- [x] Initial school administrator workflow guide documented.\n- [ ] Secure production administrator handover completed.

## Release rule

Do not load live student, payroll or financial records until every applicable gate above is completed and the final acceptance report is approved.
