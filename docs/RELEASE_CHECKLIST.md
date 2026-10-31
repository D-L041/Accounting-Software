# Production release checklist

A green frontend build or successful deployment alone is not sufficient for financial-system acceptance.

## Current status

- [x] Repository and initial architecture inspected.
- [x] Ledger posting validation strengthened in the working branch.
- [x] Posted journal and line mutation paths guarded.
- [x] Production settings reject missing secrets and non-PostgreSQL databases.
- [x] Latest full CI run #264 passed backend tests, frontend production build and API container build for code commit `7936eea`.
- [x] Session authentication, role permissions, school-level tenant isolation and owner/admin staff-login management implemented and tested.
- [x] Student, class/term fee schedules, bulk draft invoicing, invoices, payment allocation and receipt workflows implemented in API and frontend.
- [x] Supplier directory, expense categories and ledger-posted expense workflow implemented.
- [x] Core payroll employee, statutory calculation, payroll posting and account-mapping workflows implemented and tested; full statutory edge cases and all employee benefits remain outstanding.
- [x] Supplier bill submission, owner/admin approval separation, posting to payables and partial/full settlement workflows implemented and tested.
- [ ] Budgeting, procurement, purchase orders and supplier approval limits implemented.
- [x] Trial balance API and frontend report implemented.
- [x] Trial balance, balance sheet and income/expenditure statements implemented.
- [x] Posted cashbook movement report implemented (period movement only; no opening balance).
- [x] API Docker image build and database health endpoint verified in CI.
- [x] Bank statement API, ledger matching, arithmetic validation, reconciliation lock and audit trail implemented and tested.
- [ ] Bank reconciliation frontend, bank CSV import mapping and cash flow reporting implemented.
- [x] Immutable audit events for core financial posting actions and a school-scoped audit log.
- [ ] Complete CRUD audit coverage, configurable approval limits and procurement approval workflows.
- [x] Downloadable PDF receipts with school-level access checks.
- [x] Credit note and payment refund API workflows implemented and tested, including invoice balance adjustments and ledger reversals.
- [ ] Safaricom Daraja callback integration, idempotent callback handling and production M-Pesa reconciliation verified.
- [ ] Offline data queue, sync and conflict resolution implemented and tested.
- [x] Additional tenant-isolation tests added for bank statements, supplier bills and payroll employee lists.
- [ ] Independent security review and complete tenant-isolation/security test programme passed.
- [ ] Backup schedule and a real restore drill verified.
- [ ] Production API, PostgreSQL and frontend provisioned.
- [ ] Custom domain connected and HTTPS verified.
- [ ] End-to-end school acceptance tests passed, including supplier payables, payroll, refunds, trial balance and balance sheet reconciliation.
- [x] Initial school administrator workflow guide documented.
- [ ] Secure production administrator handover completed.

## Release rule

Do not load live student, payroll or financial records until every applicable gate above is completed and the final acceptance report is approved.
