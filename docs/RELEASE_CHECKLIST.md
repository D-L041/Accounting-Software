# Production release checklist

A green frontend build or successful deployment alone is not sufficient for financial-system acceptance.

## Current status

- [x] Repository and initial architecture inspected.
- [x] Ledger posting validation strengthened in the working branch.
- [x] Posted journal and line mutation paths guarded.
- [x] Trial balance service added for posted entries.
- [x] Production settings reject missing secrets and non-PostgreSQL databases.
- [x] Latest backend and frontend CI run observed and passed for the verified baseline (re-run required for subsequent commits).
- [x] Session authentication, role permissions and school-level tenant isolation implemented and tested.
- [x] Student, fees, invoices, payment allocation and receipt workflows implemented in API and frontend.
- [x] Supplier directory, expense categories and ledger-posted expense workflow implemented.\n- [ ] Payroll, budgeting, supplier bills/payables and procurement workflows implemented.
- [x] Trial balance API and frontend report implemented.\n- [x] Trial balance, balance sheet and income/expenditure statements implemented.\n- [ ] Bank reconciliation and cash flow reporting implemented.
- [x] Immutable audit events for core financial posting actions and a school-scoped audit log.\n- [ ] Complete CRUD audit coverage and financial approval workflows.
- [ ] Offline data queue, sync and conflict resolution implemented and tested.
- [ ] Independent security review and expanded tenant-isolation tests passed.
- [ ] Backup schedule and a real restore drill verified.
- [ ] Production API, PostgreSQL and frontend provisioned.
- [ ] Custom domain connected and HTTPS verified.
- [ ] End-to-end accounting acceptance tests passed, including trial balance and balance sheet reconciliation.
- [ ] User documentation and secure administrator handover completed.

## Release rule

Do not load live student, payroll or financial records until every applicable gate above is completed and the final acceptance report is approved.
