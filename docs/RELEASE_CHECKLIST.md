# Production release checklist

A green frontend build or successful deployment alone is not sufficient for financial-system acceptance.

## Current status

- [x] Repository architecture, core workflows and release risks documented.
- [x] Ledger posting validation strengthened; posted journals and lines are immutable.
- [x] Production settings reject missing secrets and non-PostgreSQL databases.
- [x] Session authentication, role permissions, school-level tenant isolation and owner/admin staff-login management implemented and covered by automated tests.
- [x] Student, class/term fee schedules, bulk draft invoicing, invoice issue, payment allocation and receipt workflows implemented in API and frontend.
- [x] Supplier directory, expense categories and ledger-posted expense workflow implemented.
- [x] Supplier bill submission, owner/admin approval separation, posting to payables and partial/full settlement workflows implemented and tested.
- [x] Category budgets, budget-versus-actual and variance monitoring implemented in API and frontend.
- [x] Purchase orders, supplier approval thresholds and sequential multi-level approval workflow implemented; complete goods-received/invoice matching and independent procurement review remain outstanding.
- [x] Trial balance, income/expenditure, balance sheet and cashbook reports implemented.
- [x] Cash-flow movement report now carries forward ledger-derived opening balances and displays closing balances; it is not yet a fully classified cash-flow statement.
- [x] Bank statement capture, ledger matching, arithmetic validation, reconciliation lock, audit trail and frontend reconciliation screen implemented and tested.
- [x] Bank CSV template download, configurable date/description/amount/reference column mapping and draft statement line import implemented in the frontend.
- [ ] Automated bank-feed integrations, broader bank-format coverage and independent CSV import acceptance tests remain outstanding.
- [x] Credit note and payment refund API workflows implemented and tested, including invoice balance adjustments and ledger reversals.
- [x] Credit note and refund frontend screen implemented.
- [x] Payroll employee, effective-dated statutory parameters, payroll calculation, posting and account mappings implemented.
- [x] Payroll statutory review found and corrected the NSSF PAYE deductibility rule; regression tests include January/February 2026 and an independent KES 100,000 benchmark.
- [x] Effective-dated NITA employer levy (KES 50 per active employee per month), separate liability mapping and employer-cost posting implemented; it is not deducted from employee net pay.
- [x] Audited CSV payroll register and PAYE, NSSF, SHIF, AHL, additional PENSION and NITA schedules implemented; statutory schedules require a posted payroll run and are audit-logged.
- [x] Employee insurance relief, mortgage-interest deduction, post-retirement medical fund, additional registered pension deductions and verified disability tax-exemption certificate support implemented with effective monthly caps and payroll-line snapshots; claim evidence references and owner/admin verification are required.
- [ ] Full payroll remains incomplete: taxable benefits in kind, official KRA P10/iTax and agency-format exports, independent Kenyan payroll-practitioner sign-off and school parallel-run acceptance remain outstanding. See `docs/PAYROLL_STATUTORY_REVIEW.md`.
- [x] Immutable audit events for core financial posting actions and a school-scoped audit log.
- [x] Purchase orders with item lines, school-configurable threshold/role rules, sequential multi-step approvals, creator/approver separation and audit events implemented.
- [ ] Complete CRUD audit coverage and independent procurement workflow review remain outstanding.
- [x] Downloadable PDF receipts with school-level access checks.
- [x] Daraja STK Push initiation, persisted attempts, callback capture, STK Query verification and duplicate-safe ledger posting implemented.
- [x] C2B callback capture/deduplication, school-scoped review queue, exact invoice-reference matching, independent Safaricom statement confirmation, duplicate transaction protection and manual receipt/ledger posting implemented.
- [ ] Daraja sandbox end-to-end tests, unattended transaction-status verification, school-specific Paybill/shortcode mapping, callback hardening and production onboarding remain outstanding. C2B automatic posting remains disabled.
- [x] PWA manifest and service worker cache the application shell and static assets only.
- [x] Encrypted IndexedDB outbox, AES-GCM device encryption, authenticated school-scoped sync endpoint, idempotency receipts and duplicate-safe expense and purchase-order draft sync implemented; synced records remain DRAFT and cannot post through the sync endpoint.
- [x] Server-side idempotent purchase-order draft sync added with allow-listed payload validation, school-scoped supplier/period checks, duplicate-key conflict detection and draft-only creation; frontend now encrypts purchase-order drafts in IndexedDB and synchronises them through the typed outbox.
- [ ] Full conflict-resolution UX (server/local comparison and explicit replacement-draft workflow), cross-device recovery and independent offline security testing remain outstanding.
- [x] Shared offline draft queue includes visible pending/needs-review status, manual sync, retained 4xx conflicts and explicit discard controls for expense and purchase-order drafts.
- [ ] Full offline operation across all modules, broader draft capture, reference-data strategy, complete conflict resolution, device-loss recovery and independent offline security testing remain outstanding. Financial posting, payments, payroll approval, reconciliation and M-Pesa remain online-only. See `docs/OFFLINE_SYNC_DESIGN.md`.
- [x] Automated tenant-isolation tests added for bank statements, supplier bills, payroll employee lists and C2B reconciliation; payroll employee/settings/run reads are restricted to authorised finance roles.
- [x] CI dependency audits for Python and npm pass with zero known vulnerabilities on the resolved dependency set.
- [ ] Independent security review, penetration testing and complete tenant-isolation programme remain outstanding.
- [x] PostgreSQL backup/restore procedure documented in `docs/BACKUP_RESTORE_RUNBOOK.md`.
- [x] CI performs a PostgreSQL custom-format dump, restores it to an isolated disposable database and verifies the restored Django migration table.
- [ ] Managed production backup schedule, retention, monitoring, PITR and a witnessed production restore drill remain outstanding.
- [ ] Pin frontend dependency versions and commit `package-lock.json`; add a reproducible Python dependency lock before production release.
- [x] Same-origin Render Docker deployment blueprint prepared; it serves the React PWA and Django API together to preserve first-party session/CSRF cookies. See `docs/RENDER_DEPLOYMENT.md`.
- [ ] Render service and managed PostgreSQL not yet provisioned; repository owner must approve the estimated monthly charges and connect the Render account.
- [ ] Generated Render HTTPS host smoke-tested after provisioning. A custom domain is optional for the pilot and has not been purchased.
- [x] St Stephen School acceptance test plan and sign-off sheet documented in `docs/ST_STEPHEN_ACCEPTANCE_TEST_PLAN.md`.
- [ ] End-to-end school acceptance tests passed using approved test data, including supplier payables, payroll, refunds, bank reconciliation, trial balance and balance sheet reconciliation.
- [ ] St Stephen School administrator and accountant acceptance sign-off received.
- [x] Initial school administrator workflow guide documented.
- [ ] Secure production administrator handover, access recovery and support ownership completed.
- [x] CI run [41234808331](https://github.com/D-L041/Accounting-Software/actions/runs/41234808331) for commit `cec53a17` passed: Django checks, migration drift check, migrations, isolated PostgreSQL backup/restore smoke test, backend tests (107 passed), frontend production build, Docker image build and Python/npm dependency audits.

## Release rule

Do not load live student, payroll or financial records until every applicable gate above is completed and the final acceptance report is approved. Do not merge or deploy this branch as a production release while any blocker above remains open.
