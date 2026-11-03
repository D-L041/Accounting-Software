# Implementation plan

## Phase 1 — accounting foundation

**Implemented:** school-scoped authentication and role permissions, tenant isolation, financial periods, chart of accounts, balanced double-entry ledger, immutable posted journals/lines, trial balance and core audit events.

**Remaining:** complete CRUD audit coverage, configurable approval limits, controlled reversals for all correction cases, broader penetration testing and independent accounting controls review.

## Phase 2 — school operations and billing

**Implemented:** student/class/academic-year records, fee items, class/term fee schedules, duplicate-safe bulk draft invoice generation, invoice issue, cash/bank/M-Pesa receipts, payment allocations, PDF receipts, credit notes and refunds.

**Remaining:** full acceptance testing for every invoice/refund edge case, payment-provider production onboarding and school-specific payment configuration.

## Phase 3 — cash management and procurement

**Implemented:** supplier directory, expense categories, draft and posted expenses, supplier bills/payables, owner/admin approval separation, partial/full supplier-bill settlement, budgets, bank statement capture, manual matching and reconciliation audit trail. Cashbook and cash-flow movement reports include ledger-derived opening balances.

**Remaining:** purchase orders, supplier approval thresholds, multi-level procurement approvals, CSV bank import mapping, bank feeds, petty-cash controls and a fully classified cash-flow statement.

## Phase 4 — payroll

**Implemented:** employee records, effective-dated Kenyan statutory rules, payroll draft calculation, payroll ledger mappings and posting. The NSSF employee contribution PAYE deductibility rule was corrected and benchmark regression tests added.

**Remaining:** insurance relief, mortgage-interest and post-retirement medical deductions, additional pension contributions, exemption certificates, taxable non-cash benefits, NITA employer levy, statutory schedules/exports, complete payroll edge-case testing and independent Kenyan payroll-practitioner sign-off. See `docs/PAYROLL_STATUTORY_REVIEW.md`.

## Phase 5 — payment provider integration

**Implemented:** Daraja STK Push initiation, persisted attempts, callback capture and STK Query verification before payment posting. C2B notifications are captured, deduplicated and manually reconciled after an independent Safaricom statement match.

**Remaining:** sandbox end-to-end tests, production callback hardening, school-specific shortcode/Paybill mapping and transaction-status verification before any unattended C2B posting. Automatic C2B posting remains disabled.

## Phase 6 — client and offline operation

**Implemented:** responsive React/TypeScript frontend, secure login, school-aware workflows, bank reconciliation, credit-note/refund, payroll, procurement and budget screens. PWA manifest and service worker cache the static application shell only.

**Remaining:** complete accessibility and end-to-end browser tests, offline draft outbox, authenticated sync API, idempotency, conflict UI and security/privacy tests. Financial writes remain online-only until the complete sync design is implemented and tested. See `docs/OFFLINE_SYNC_DESIGN.md`.

## Phase 7 — assurance and operations

**Implemented:** backend unit/integration tests, PostgreSQL CI, frontend production build, API container build, selected tenant-isolation tests and backup/restore runbook.

**Remaining:** final branch-head CI pass, full tenant-isolation suite, independent security review, dependency scanning, managed backup schedule, witnessed restore drill, production smoke tests and St Stephen School acceptance testing. See `docs/BACKUP_RESTORE_RUNBOOK.md` and `docs/RELEASE_CHECKLIST.md`.

## Phase 8 — deployment and handover

**Remaining:** provision managed PostgreSQL and Django API hosting, configure protected environment secrets, deploy frontend, connect domain and HTTPS, enable monitoring/backups, perform administrator training and hand over access/recovery procedures.

No real school records, payroll figures, statutory rates or production credentials are to be invented. Production release requires independent verification of all acceptance criteria and written school sign-off.
