# Offline synchronisation design and release boundary

## Current behaviour

The frontend is installable as a progressive web app and its service worker caches the application shell and static assets. It deliberately does not cache authenticated API responses. When disconnected, the app displays an offline notice and blocks financial writes. There is currently no durable offline outbox, server sync endpoint or conflict-resolution workflow.

This is intentional: cached financial or pupil records on a shared school device create confidentiality and data-protection risks, and silently replaying a payment or journal could duplicate accounting entries.

## Approved offline boundary

The first synchronisation release should support **draft capture only**. It must never post or settle financial records while offline.

Allowed for a first controlled pilot:
- Draft expense capture, pending online server validation.
- Draft purchase-request capture after a purchase-request model exists.
- Non-sensitive interface preferences.

Remain online-only:
- Invoice issue, payment receipt, allocation, refund and credit note posting.
- Journal creation/posting, period lock, bank statement reconciliation and cashbook posting.
- Payroll calculation approval, payroll posting and statutory remittance.
- M-Pesa STK Push, C2B reconciliation and any callback verification.
- Supplier bill approval, posting and settlement.
- User, role, school, employee and pupil identity changes until their offline privacy requirements are separately approved.

## Required client outbox

1. Use IndexedDB, not localStorage, for the outbox.
2. Encrypt payloads using Web Crypto AES-GCM. Keep a non-extractable key in IndexedDB and bind each queued item to the authenticated user and active school. Encryption reduces at-rest exposure but does not protect against a compromised browser session or XSS.
3. Queue an immutable envelope containing a UUID idempotency key, schema version, resource type, draft payload, user ID, school ID, creation time and the server revision observed when editing began.
4. Never store session cookies, CSRF tokens, passwords, Daraja secrets or full server API responses in the outbox.
5. Prompt users to sync or discard pending drafts before logout, account switch or school switch. Purge queued records and keys on explicit discard, logout or account removal.
6. Show queued, syncing, conflict and rejected states. A failed sync must not delete the local draft.

## Required server sync contract

- Require a fresh authenticated session, CSRF validation, active school membership and the role required for that draft type.
- Accept one operation at a time initially; enforce a unique (school, user, idempotency_key) constraint so retries cannot create duplicates.
- Validate the entire payload on the server. Never trust client-supplied school IDs, account IDs, supplier IDs, financial period IDs or user IDs.
- Re-check that all related records belong to the active school and that the financial period is open.
- Use optimistic concurrency (base_revision / If-Match) for edits. A stale base revision must return a conflict containing the server version and a reason; never apply last-write-wins.
- Return stable outcomes: accepted, already-applied, conflict or rejected. Persist the idempotency outcome in the same database transaction as draft creation.
- Do not expose a generic endpoint capable of posting arbitrary models or journals.

## Conflict resolution

The user must compare the local draft with the current server record and explicitly choose to keep the server version, discard the local draft or create a new draft from the local values. The server must validate any replacement as a new operation. There is no automatic merge for financial amounts, account mappings, dates, student identifiers or supplier references.

## Required tests before enabling

- Duplicate delivery, repeated retries and interrupted sync.
- User logout, user switch, school switch and role revocation.
- Cross-school foreign-key substitution and inactive-school access.
- Stale revision conflict and manual resolution.
- Closed financial period, invalid account, inactive supplier and invalid amount.
- Device restart, storage quota failure, corrupt encrypted item and missing key.
- Clock skew, daylight-saving/time-zone changes and duplicate browser tabs.
- Explicit proof that no offline action can post a ledger journal, issue an invoice, record a receipt or trigger payroll/M-Pesa.

## Release gate

Do not describe Precious SchoolBooks as fully offline-capable until the outbox, authenticated sync API, idempotency, conflict UI and the complete test set above are implemented and independently tested. Until then, only the static application shell is available offline and all financial writes remain online-only.
