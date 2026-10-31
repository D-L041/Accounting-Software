# St Stephen School — acceptance test plan

## Purpose and status

Use this plan with synthetic/test records in a controlled acceptance environment. It is a test script, not evidence that St Stephen School has accepted the system. Do not load real pupil, employee, parent or financial data until production and privacy controls are approved.

Record the release commit, environment, date, test operator, school representative and evidence location before starting.

## A. School setup and access control

1. Create the St Stephen School workspace with KES currency, Africa/Nairobi time zone, academic year and financial periods.
2. Create separate owner, administrator, accountant, bursar and viewer accounts.
3. Confirm each role can access only its permitted screens and actions.
4. Attempt cross-school access to student, invoice, payment, account, payroll, supplier bill, bank statement and C2B notification IDs. Every cross-school attempt must be denied without leaking record details.
5. Disable a user's membership and confirm access is revoked on the next request.
6. Confirm password reset, session expiry, logout and CSRF protections.

**Pass evidence:** role/action matrix, tenant-isolation results and audit events.

## B. Chart of accounts and ledger

1. Configure cash, bank, M-Pesa clearing, receivables, income, expense, payroll liabilities and supplier payable accounts.
2. Create a balanced test journal and post it.
3. Attempt to post an unbalanced journal, a journal outside the period and a journal in a locked period.
4. Attempt to edit/delete posted journals and journal lines.
5. Confirm trial balance debits equal credits and reports include posted entries only.
6. Confirm adjustments/corrections use supported reversal, credit-note or refund workflows rather than changing posted history.

**Pass evidence:** posted journal, rejected attempts, trial balance and audit log.

## C. Fees, invoices and receipts

1. Create fee items and a class/term fee schedule.
2. Generate bulk draft invoices twice and confirm the second run does not create duplicate invoices.
3. Issue a draft invoice and confirm the receivables/income journal is balanced.
4. Record partial and full payments with allocations; confirm invoice balances and receipt PDFs.
5. Attempt overpayment, duplicate M-Pesa transaction reference and cross-school invoice allocation.
6. Confirm all failed attempts leave balances and ledger unchanged.

**Pass evidence:** invoice register, receipt copies, allocation report and ledger entries.

## D. Credit notes and refunds

1. Issue a credit note against an eligible invoice.
2. Confirm invoice balance and revenue/receivables journal effects.
3. Refund a valid payment using the supported workflow.
4. Attempt refund above the refundable amount and duplicate refund.
5. Confirm posted corrections remain auditable and do not mutate original receipts or journals.

**Pass evidence:** credit note, refund record, original payment and balanced reversal entries.

## E. Expenses, supplier bills, budgets and procurement

1. Create a supplier and expense category linked to an expense account.
2. Create a draft expense, post it and confirm the balanced cash/bank/M-Pesa journal.
3. Create a supplier bill; confirm the creator cannot approve their own bill where separation is required.
4. Approve, post and partially settle a supplier bill; confirm payable balances and settlement journals.
5. Attempt cross-school supplier/account/period references and duplicate supplier invoice references.
6. Create a category budget and compare actual posted expenditure against budget.
7. Record procurement gaps separately: purchase orders, multi-level approval limits and full purchasing lifecycle are not yet implemented.

**Pass evidence:** expense register, supplier bill approvals, payable ageing/balance, budget variance report and unresolved procurement-gap log.

## F. Bank reconciliation and cash flow

1. Import/capture a test bank statement with opening and closing balances.
2. Match statement lines to posted bank journal lines.
3. Attempt a wrong-amount match, duplicate match, unmatched reconciliation and statement arithmetic mismatch.
4. Reconcile a fully matched statement and confirm it becomes locked/audited.
5. Verify cash-flow opening balance is derived from previously posted cash/bank/M-Pesa entries and closing balance equals opening plus net movement.
6. Record CSV import and bank-feed gaps; manual statement entry/matching is the current supported path.

**Pass evidence:** reconciled statement, match report, cash-flow report and ledger tie-out.

## G. Payroll — controlled test only

Use synthetic employees and compare the output independently with a Kenyan payroll professional's calculation for the exact pay period.

1. Verify the effective NSSF rule for the month, including January/February 2026 rate transition.
2. Test the documented KES 50,000 and KES 100,000 benchmark cases.
3. Confirm employee NSSF, SHIF and Housing Levy, PAYE, net pay and employer contributions.
4. Confirm payroll posting creates a balanced journal and the run becomes immutable.
5. Verify remittance schedules, insurance relief, mortgage interest, post-retirement medical fund, additional pension, exemptions, taxable benefits, NITA and exports before marking payroll production-ready.

**Pass evidence:** signed independent payroll comparison and statutory gap sign-off. Payroll must not be used for live pay until all items in PAYROLL_STATUTORY_REVIEW.md are resolved.

## H. M-Pesa / Daraja

1. Use Safaricom sandbox credentials only in the acceptance environment.
2. Verify STK Push initiation, persisted attempt, callback capture, STK Query verification, duplicate callback and failed/mismatched amount/phone cases.
3. Verify C2B validation/confirmation capture, duplicate transaction ID and invalid/oversized payload rejection.
4. Reconcile C2B only after an operator independently matches the Safaricom statement and the invoice reference exactly.
5. Confirm automatic C2B posting remains disabled until transaction-status verification and school-specific Paybill mapping are implemented and approved.
6. Never run live-money tests without Safaricom and school approval.

**Pass evidence:** sandbox request/response logs with secrets redacted, test receipt and audit trail.

## I. Offline and security

1. Install the PWA and verify the static application shell opens offline.
2. Confirm authenticated API responses are not cached.
3. Confirm all financial writes are blocked offline; do not simulate or approve offline posting.
4. Run the automated Python/npm dependency audits and tenant-isolation tests.
5. Complete independent penetration testing, authorization review, backup restore drill and incident-response exercise.

**Pass evidence:** offline test log, CI run, security report and witnessed restore report.

## J. Final acceptance and sign-off

All blockers in RELEASE_CHECKLIST.md must be closed or formally accepted with a risk owner and deadline. The school representative, accountant, technical operator and service owner must sign the final test record. Any failed scenario must be logged with severity, reproduction steps, assigned owner and retest evidence.

| Role | Name | Signature | Date |
|---|---|---|---|
| School head / authorized representative |  |  |  |
| School bursar / accountant |  |  |  |
| DKL Accounting Services representative |  |  |  |
| Technical / security reviewer |  |  |  |

**Current acceptance status:** Not yet executed or signed. Production release remains blocked.
