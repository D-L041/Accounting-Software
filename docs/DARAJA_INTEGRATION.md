# Safaricom Daraja integration — staged implementation

## Implemented in this branch

- Authenticated school-scoped STK Push initiation against an issued invoice balance.
- Kenyan MSISDN normalisation and amount rounding to whole KES for STK Push.
- OAuth client-credentials token acquisition and STK Push request construction.
- Persisted STK attempts with unique CheckoutRequestID and callback state.
- STK callback capture followed by Daraja STK Query before attempting a ledger posting.
- Payment posting through the existing billing service, preserving receipt numbering, invoice allocation, double-entry posting and external-reference uniqueness.
- C2B validation and confirmation endpoints. C2B confirmations are durably deduplicated by TransID and held for verification/reconciliation; they are deliberately not posted automatically yet.

## Required environment variables

Set these as server-side secrets only. Never expose them to the browser or commit them.

- DARAJA_ENV=sandbox (use production only after Safaricom approval)
- DARAJA_CONSUMER_KEY
- DARAJA_CONSUMER_SECRET
- DARAJA_SHORTCODE
- DARAJA_PASSKEY
- DARAJA_CALLBACK_URL=https://YOUR-API-DOMAIN/api/daraja/callbacks/stk/

The API must be publicly reachable over HTTPS. Do not use a Vercel frontend URL as the callback unless it routes to the Django API.

## Callback registration

Register the C2B validation and confirmation endpoints with Safaricom using the exact public API URLs:

- /api/daraja/callbacks/c2b/validation/
- /api/daraja/callbacks/c2b/confirmation/

C2B callbacks are only captured at this stage. Before enabling automatic posting, implement and test the Daraja transaction-status query flow, resolve BillRefNumber to an invoice using an explicit school/paybill mapping, enforce amount/balance checks, and post with the originating transaction ID as the idempotency reference. Unknown or ambiguous references must go to manual review.

## Go-live safety gates

1. Complete Daraja sandbox tests for successful, cancelled, timed-out, duplicate and malformed STK callbacks.
2. Add transaction-status verification and reconciliation for C2B confirmations before posting them.
3. Verify callback endpoint abuse controls, request-size limits, rate limits, monitoring and retry handling. Daraja callbacks are not authenticated by Django sessions; do not treat an unauthenticated callback body alone as proof of payment.
4. Configure real shortcode, passkey and approved production credentials in the hosting secret manager.
5. Complete Safaricom's production onboarding/go-live process and test a controlled live transaction before school rollout.

No live payment processing should be enabled until the remaining C2B verification, callback security review and production approval gates pass.
