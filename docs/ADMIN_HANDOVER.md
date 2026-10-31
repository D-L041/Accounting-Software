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
- ALLOWED_HOSTS — exact Render hostname (for the initial Blueprint: `precious-schoolbooks.onrender.com`), no wildcard.
- DATABASE_URL — Render-managed PostgreSQL connection string.
- Keep the React frontend and Django API on the same origin for the initial session/CSRF authentication model. The current Render Blueprint serves both from one service; CORS/CSRF origin lists are not required for same-origin traffic.

Daraja variables only after Safaricom onboarding:
- DARAJA_ENV=sandbox for acceptance testing; change to production only after Safaricom onboarding and release approval.
- DARAJA_CONSUMER_KEY
- DARAJA_CONSUMER_SECRET
- DARAJA_SHORTCODE
- DARAJA_PASSKEY
- DARAJA_CALLBACK_URL
- DARAJA_TRANSACTION_TYPE

Keep all secrets in the host's protected environment configuration. Use sandbox credentials only in a non-production environment. Never activate live M-Pesa until callback URLs, shortcode mapping, transaction verification, test transactions and reconciliation controls are signed off.

## 3. Deployment sequence

1. Review `docs/RENDER_DEPLOYMENT.md` and the root `render.yaml`; confirm the resource sizes and monthly charges before creating anything.
2. Confirm the approved commit and passing CI checks on the exact commit to deploy.
3. Connect the GitHub repository to Render and create the Blueprint only after the repository owner approves the billing and service creation.
4. Provision managed PostgreSQL in the same Frankfurt region; configure backup retention and complete an isolated restore drill.
5. Configure the generated secret, exact `ALLOWED_HOSTS`, database URL and Daraja sandbox values in Render's protected environment settings.
6. Run `python manage.py check --deploy`, apply migrations through the reviewed pre-deploy command and verify the health endpoint.
7. Confirm the React frontend and Django API are served from the same HTTPS origin and that login, session cookies and CSRF protection work.
8. Keep automatic deploys disabled until the production release gate is approved; run smoke tests using synthetic data only.

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

The repository is not yet a production deployment. A Render same-origin pilot Blueprint is prepared in `render.yaml`, but no Render service, managed PostgreSQL instance or domain has been provisioned, and no Safaricom sandbox credentials have been configured. The current offline outbox covers expense drafts only; purchase orders and multi-level approvals are implemented online, but offline purchase order capture, full offline operation, complete payroll claims/exports, bank-feed integrations and independent security/restore/acceptance sign-offs remain release blockers. Do not hand over as production-ready until the release checklist is complete.
