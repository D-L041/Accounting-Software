# Precious SchoolBooks — initial administrator guide

This guide describes the workflows currently implemented in the development build. Menu labels may change as the product is completed.

## First access

1. Create the initial administrator account through the secure deployment console using Django's `createsuperuser` command.
2. Sign in to Precious SchoolBooks.
3. Create the school's workspace. The creator becomes its owner.
4. Use **Settings → School user access** to create staff logins. Assign only the role each staff member needs. Give each new staff member a temporary password through a secure channel.

There is no public self-registration page. Staff accounts are created by an authorised school owner or administrator.

## Initial school configuration

Before entering transactions, configure:

1. Academic year and classes/streams.
2. Financial period with correct start and end dates.
3. Chart of accounts. Set up the school's receivables, cash, bank, M-Pesa clearing, fee income and expense accounts.
4. Fee items mapped to income accounts.
5. Billing account mappings for receivables, cash, bank and M-Pesa.
6. Expense categories mapped to expense accounts.
7. Students and their classes.

Use the correct financial period for the date of each transaction. Locked periods cannot accept new postings.

## Fees and receipts

- Create a class/term fee schedule with its academic year, class, financial period, invoice date, due date and one or more fee items.
- Generate draft invoices for active students in that class. The operation skips students who already have an invoice from that schedule, so it can be safely retried.
- Review each draft invoice and issue it. Issuing posts the receivable and fee income to the double-entry ledger.
- Record each payment against one or more open invoices using cash, bank or M-Pesa as the method. Enter the M-Pesa/bank reference when available.
- Download the PDF receipt from **Payments & Receipts**.

M-Pesa receipts are still entered manually using a transaction reference. Safaricom Daraja callbacks are not yet connected.

## Expenses

- Create supplier records and expense categories.
- Record an expense as a draft with its date, period, category, amount, payment method and optional supplier.
- Review the details and post the expense. Posting creates the balanced ledger entry and makes the posted expense immutable.

### Supplier bills and payables

- Create a supplier bill draft with its supplier, supplier invoice number, bill date, due date, expense category, financial period, amount and accounts-payable liability account.
- Submit the bill for approval. The submitter cannot approve the same bill.
- Only a school owner or administrator can approve a submitted bill.
- Post an approved bill to record Dr Expense / Cr Accounts Payable.
- Record full or partial payments against posted bills. Each payment reduces the payable and posts Dr Accounts Payable / Cr the selected cash, bank or M-Pesa account.
- Submitted, approved and posted bills cannot be edited. Posted payments are immutable.

## Bank reconciliation

The bank statement API supports statement headers and transaction lines, matching statement lines to posted ledger lines, arithmetic checks and locking a reconciled statement. Reconciliation is currently an API workflow; a dedicated bank reconciliation screen, CSV import mapping and automated bank-feed integration remain to be completed. The existing cashbook report is not itself a reconciliation.

## Credit notes and refunds

- Create a draft credit note against an issued invoice and allocate amounts to its original invoice lines.
- Post the credit note to debit fee income and credit student receivables.
- Record a refund against a previously posted payment and the invoice allocation to which it relates.
- A refund posts Dr Student Receivables / Cr the selected cash, bank or M-Pesa account and reopens the relevant invoice balance.
- Credit notes and refunds are immutable once posted. They cannot exceed the original invoice-line value or payment allocation.

## Staff and payroll

- Register employees with staff number, names, job title, basic monthly salary and tax-residency status.
- Configure the payroll expense and liability ledger accounts before posting a payroll run.
- Create a monthly draft payroll for an open financial period. The system applies effective-dated NSSF, SHIF, Affordable Housing Levy and PAYE rules and calculates employee net pay and employer contributions.
- Review the payroll lines before posting. Posting creates the salary expense and statutory/payroll liabilities in the double-entry ledger.
- Effective-dated statutory rules and PAYE bands can be read by school members; only school owners and administrators can create school-specific overrides.

Payroll currently covers basic monthly salary and the listed statutory calculations. It does not yet cover all allowances, benefits-in-kind, insurance relief, mortgage interest, voluntary pension schemes, leave, overtime, advances, payslip delivery or statutory return filing. Confirm current rules and employee-specific deductions with a qualified Kenyan payroll/accounting professional before using live payroll.

## Reports and audit

- **Reports** contains trial balance, income and expenditure, and balance sheet reports based on posted ledger entries.
- **Cashbook & Banks** shows posted movements through the configured cash, bank and M-Pesa accounts for the selected period. Movement balances start at zero and do not include opening balances. It is not a bank reconciliation.
- **Audit Log** records important school and financial actions. Audit events are read-only.

## Important limitations

- This is a development build and must not be used for live school records until the production release checklist is approved.
- Transactions are disabled while offline. Offline data storage and synchronisation are not implemented.
- Payroll, supplier payables, credit notes/refunds and bank reconciliation have initial tested API workflows. The payroll feature does not yet cover every employee benefit or deduction, and bank reconciliation still needs a dedicated user interface and bank-file import workflow.
- Automated Safaricom Daraja callbacks, full offline/PWA queue and conflict resolution remain outstanding.
- Opening balances must be entered through controlled journal entries; reports do not invent them.
- Posted journal entries, expenses, supplier bill payments, credit notes, refunds and payroll runs are immutable. Use controlled reversal/adjustment workflows; do not edit posted financial history.

Always test with synthetic data in staging before any live rollout.
