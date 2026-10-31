# Production release checklist

A green frontend build or successful deployment alone is not sufficient for financial-system acceptance.

## Current status

- [x] Repository and initial architecture inspected.
- [x] Ledger posting validation strengthened in the working branch.
- [x] Posted journal and line mutation paths guarded.
- [x] Trial balance service added for posted entries.
- [x] Production settings reject missing secrets and non-PostgreSQL databases.
- [ ] CI test run observed and passed.
- [ ] Authentication, role permissions and school-level tenant isolation implemented and tested.
- [ ] Student, fees, invoices, payment allocation and receipt workflows implemented.
- [ ] Expense, supplier, payroll, budgeting and procurement workflows implemented.
- [ ] Bank reconciliation and complete financial reports implemented.
- [ ] Audit event capture and financial approval workflows implemented.
- [ ] Offline data queue, sync and conflict resolution implemented and tested.
- [ ] Security review and tenant-isolation tests passed.
- [ ] Backup schedule and a real restore drill verified.
- [ ] Production API, PostgreSQL and frontend provisioned.
- [ ] Custom domain connected and HTTPS verified.
- [ ] End-to-end accounting acceptance tests passed, including trial balance and balance sheet reconciliation.
- [ ] User documentation and secure administrator handover completed.

## Release rule

Do not load live student, payroll or financial records until every applicable gate above is completed and the final acceptance report is approved.
