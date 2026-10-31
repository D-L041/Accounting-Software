# Offline synchronisation design and release boundary

## Current implementation — controlled pilot stage

The frontend is installable as a progressive web app and its service worker caches the application shell and static assets only. An encrypted IndexedDB outbox now supports **expense draft capture** while disconnected, using AES-GCM and a non-extractable browser key scoped to the signed-in user and school. The UI shows queued drafts, offers manual synchronisation when online and allows explicit local discard. The outbox never stores passwords, session cookies, CSRF tokens, Daraja secrets or API response bodies.

When connectivity returns, the client sends each expense draft to the authenticated school-scoped sync endpoint. The server validates membership, write role, school-owned category/period/supplier references and the expense serializer; it stores an idempotency receipt and creates a DRAFT expense only. Repeated deliveries return the original outcome, and reusing a key with different data returns a conflict. The endpoint cannot post a journal. Synced drafts must be reviewed and posted online through the normal expense workflow.

This is not yet full offline operation across all modules. Reference lists must already be loaded in the current session before disconnection; authenticated API responses and pupil, employee, payroll and ledger data are not cached. Offline capture beyond expense drafts, richer conflict resolution and recovery, device-loss recovery and independent offline security testing remain outstanding.

This is intentional: cached financial or pupil records on a shared school device create confidentiality and data-protection risks, and silently replaying a payment or journal could duplicate accounting entries.

## Approved offline boundary

The first synchronisation release supports **draft capture only**. It must never post or settle financial records while offline.

Implemented in the current pilot:
- Encrypted draft expense capture, pending online server validation and idempotent synchronisation.

Planned after the corresponding workflows and privacy controls are complete:
- Draft purchase-request capture after a purchase-request model exists.
- Additional non-posting drafts where offline data exposure has been reviewed.
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
- The current expense-draft endpoint accepts one operation at a time and enforces a unique (school, user, idempotency_key) constraint so retries cannot create duplicates. Extend the same contract separately for each future draft resource.
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

Do not describe Precious SchoolBooks as fully offline-capable until all approved modules have durable encrypted draft storage, authenticated sync APIs, idempotency, visible retry/conflict/discard controls and the complete test set above, followed by independent security testing. The current pilot supports encrypted expense drafts only. All financial posting, receipt allocation, payroll approval, reconciliation and M-Pesa actions remain online-only.
