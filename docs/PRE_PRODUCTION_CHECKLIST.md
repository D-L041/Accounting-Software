# Precious SchoolBooks — Pre-production readiness

This checklist reflects the implementation state of the feature branch. A feature being implemented does not mean it has passed independent review or is approved for production.

## Implemented in the application branch

- [x] Bank statement capture, ledger-line matching and reconciliation API.
- [x] Bank reconciliation frontend workflow.
- [x] Credit note creation and posting API and frontend register.
- [x] Payment refund API and frontend capture workflow.
- [x] Payroll employee records, configurable effective-dated statutory rules, PAYE bands, draft payroll calculations and ledger posting.
- [x] Payroll frontend for employee maintenance, account mappings, draft runs and posting.
- [x] Regular cash allowances and recurring deductions on employee payroll profiles.
- [x] Supplier records, supplier bills, submit/approve/post workflow, separation-of-duties check and part/full payment API.
- [x] Supplier procurement and approval frontend.
- [x] Expense budgets by period and category with actual-versus-budget reporting.
- [x] Direct cash/bank movement report based on posted entries.

## Still required before production

- [ ] Independent Kenyan payroll review and signed-off statutory test cases. The current calculator does not yet cover every possible payroll item/relief (for example insurance relief, pension and post-retirement medical deductions, benefits-in-kind, irregular earnings and statutory edge cases). Validate all applicable inputs and rates with a qualified Kenyan payroll/tax reviewer before use.
- [ ] Review cash-flow report classification and opening/closing balances. Current direct movement report deliberately excludes opening balances and does not classify investing/financing flows.
- [ ] Safaricom Daraja sandbox certification, production credentials, callback URL registration, signature/validation controls, idempotency and reconciliation tests.
- [ ] Offline PWA queue, durable sync, idempotency keys, conflict review/resolution and explicit safeguards against duplicate financial postings.
- [ ] Independent penetration test, authorization/tenant-isolation review, dependency review and remediation.
- [ ] Automated database backup policy, encrypted off-site backup, restore drill and documented recovery objectives.
- [ ] St Stephen School user acceptance tests, opening balances, chart-of-accounts review, fee and payroll parallel-run reconciliation, user training and sign-off.
- [ ] Production hosting for Django and PostgreSQL, secret management, migrations, monitoring, alerts, backups and operational runbook.
- [ ] Domain DNS, HTTPS/TLS, secure CORS/CSRF/cookie configuration and administrator handover.

## Release rule

Do not merge the feature branch or enable production financial transactions until the backend and frontend CI checks pass on the final commit, all external/security/restore/pilot gates are signed off, and the owner explicitly approves release.
