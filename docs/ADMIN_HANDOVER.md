# Production administrator handover checklist

This checklist is for the deployment owner and the nominated school administrator. It does not mean that production hosting or access has already been provisioned.

## 1. Hosting owner and access

- Record the legal service owner, data controller, technical operator and emergency contact.
- Confirm who owns the GitHub repository, API host, database, frontend host, DNS zone and billing accounts.
- Enforce MFA for all hosting, GitHub, database and domain-owner accounts.
- Use separate named administrator accounts; do not share the owner login.
- Store break-glass recovery instructions in the approved password manager.

## 2. Backend environment

Configure these as protected host environment variables or secret-manager values. Never commit production values to Git or share them in chat.

Required:
- DEBUG=False
- SECRET_KEY — long, random production-only secret.
- DATABASE_URL — managed PostgreSQL connection string.
- ALLOWED_HOSTS — exact API hostnames, no wildcard.
- CORS_ALLOWED_ORIGINS — exact frontend origin(s), no wildcard.
- CSRF_TRUSTED_ORIGINS — exact HTTPS frontend origin(s).

Daraja variables only after Safaricom onboarding:
- DARAJA_ENV=production
- DARAJA_CONSUMER_KEY
- DARAJA_CONSUMER_SECRET
- DARAJA_SHORTCODE
- DARAJA_PASSKEY
- DARAJA_CALLBACK_URL
- DARAJA_TRANSACTION_TYPE

Keep all secrets in the host's protected environment configuration. Use sandbox credentials only in a non-production environment. Never activate live M-Pesa until callback URLs, shortcode mapping, transaction verification, test transactions and reconciliation controls are signed off.

## 3. Deployment sequence

1. Confirm the approved commit and passing CI checks on the exact commit to deploy.
2. Provision managed PostgreSQL, enable backups/PITR and complete an isolated restore drill.
3. Configure the API environment and run python manage.py check --deploy.
4. Apply database migrations in a controlled release window.
5. Run python manage.py collectstatic --noinput.
6. Start the API using the reviewed production process configuration (for example Gunicorn behind HTTPS).
7. Provision the frontend host and set the API base URL using the documented frontend environment variable.
8. Configure exact CORS/CSRF origins, HTTPS, DNS and monitoring.
9. Run production smoke tests using test data only before loading school records.

## 4. Initial school setup

- Create the school workspace and verify the legal school name, currency (KES), time zone (Africa/Nairobi), financial year and academic year.
- Configure a school-scoped chart of accounts and financial periods.
- Configure receivables, cash, bank and M-Pesa clearing accounts.
- Configure fee items, classes/streams, term fee schedules and invoice numbering.
- Configure expense categories, supplier approval responsibilities and budget categories.
- Configure payroll ledger accounts and validate every effective-dated statutory rule against the payroll period.
- Create named users and assign the least-privilege role needed for each person.
- Confirm that users cannot view or change another school's records.

## 5. Acceptance and handover

- Complete the signed school acceptance test plan with the headteacher, bursar and accountant.
- Verify trial balance, balance sheet, income/expenditure, cash-flow movement, bank reconciliation, credit notes, refunds, payroll and supplier payables.
- Verify backup restoration and recovery contacts.
- Train administrators on user management, role changes, period locks, audit history, receipts and incident escalation.
- Hand over documentation, support contact, backup status and recovery instructions.
- Record acceptance date, version/commit, named approvers and unresolved limitations.

## 6. Explicit limitations at current handover stage

The repository is not yet a production deployment. The connected Vercel account context returned no accessible teams/projects, and no API host, managed PostgreSQL instance, domain or live Safaricom credentials have been provisioned through this workflow. Offline sync, complete payroll claims/exports, purchase orders and independent security/restore/acceptance sign-offs remain release blockers. Do not hand over as production-ready until the release checklist is complete.
