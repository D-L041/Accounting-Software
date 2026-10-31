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

M-Pesa is currently recorded from a reference entered by the user. Automated Safaricom Daraja callbacks and statement matching are not yet implemented.

## Expenses

- Create supplier records and expense categories.
- Record an expense as a draft with its date, period, category, amount, payment method and optional supplier.
- Review the details and post the expense. Posting creates the balanced ledger entry and makes the posted expense immutable.

Supplier bills/payables, purchase approvals and procurement are not yet implemented.

## Reports and audit

- **Reports** contains trial balance, income and expenditure, and balance sheet reports based on posted ledger entries.
- **Cashbook & Banks** shows posted movements through the configured cash, bank and M-Pesa accounts for the selected period. Movement balances start at zero and do not include opening balances. It is not a bank reconciliation.
- **Audit Log** records important school and financial actions. Audit events are read-only.

## Important limitations

- This is a development build and must not be used for live school records until the production release checklist is approved.
- Transactions are disabled while offline. Offline data storage and synchronisation are not implemented.
- Payroll, statutory deductions, budgets, supplier payables, bank reconciliation, credit notes/refunds and automated M-Pesa integration remain outstanding.
- Opening balances must be entered through controlled journal entries; reports do not invent them.
- Posted journal entries and expenses cannot be edited. Controlled reversal/adjustment workflows are still being developed.

Always test with synthetic data in staging before any live rollout.
