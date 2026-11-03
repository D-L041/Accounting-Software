# Independent security assessment plan — Precious SchoolBooks

## Status

**Independent assessment not yet performed.** The repository has automated tenant-isolation tests, role checks, dependency audits and CI build checks. These are useful engineering controls, not a penetration test or independent security certification.

## Required assessment environment

- A dedicated Render staging environment, separate from any production service.
- Synthetic St Stephen School data only; no real pupil, parent, employee, bank or payroll records.
- Separate staging credentials and Daraja sandbox credentials stored in the provider's secret manager.
- A named independent assessor authorised in writing by the service owner and school data controller.
- A documented test window, rollback contact and incident escalation path.

## Minimum scope

1. **Identity and sessions:** authentication, password reset, session expiry/revocation, CSRF, cookie flags, brute-force controls and privilege changes.
2. **Tenant isolation:** attempt cross-school reads/writes for every school-scoped API, including IDs in nested resources, exports, receipts, files, audit events and offline sync.
3. **Role enforcement:** viewer, bursar, accountant, administrator and owner permissions; approval separation; self-approval; staff offboarding.
4. **Financial integrity:** journal immutability, idempotency, duplicate payment/refund/webhook handling, concurrent posting, period locks, approval workflow bypass and rounding/tampering.
5. **Daraja integration:** callback authenticity/validation, replay, malformed payloads, amount/phone/reference mismatch, duplicate transaction IDs, rate limits and secret exposure.
6. **Offline/PWA:** IndexedDB encryption and key scope, shared-device access, sign-out, account switching, storage inspection, service-worker cache review, tampered queue payloads, retry and conflict behavior.
7. **Application security:** injection, XSS, CSRF, SSRF, insecure direct object references, unsafe file handling, security headers, CORS, dependency and container image review.
8. **Data protection and operations:** logging of personal data, secrets management, backups, restore access, administrator recovery, monitoring and incident response.

## Evidence and exit criteria

The assessor must deliver:
- Scope, methods, dates, environment and limitations.
- Findings ranked by severity with reproducible evidence and affected endpoints.
- A remediation register with owner and target date.
- Retest evidence for every critical/high finding and agreed treatment for medium/low findings.
- Written residual-risk acceptance by the service owner and school data controller.

No production data should be loaded and no production deployment should be approved while critical/high findings remain open.

## Existing automated controls (not a substitute for the assessment)

- CI runs Django checks, migration drift checks, backend tests, frontend production build and container build.
- CI audits Python and npm dependencies.
- Automated tests cover tenant isolation for several finance workflows, including payroll employee/settings/run access restrictions.
- CI performs an isolated PostgreSQL backup/restore smoke test.
- The offline outbox encrypts queued expense and purchase-order drafts and retains server-rejected drafts for review.

**Release gate:** keep independent security review and penetration testing open until an external assessor has completed the scope above and signed the report.
