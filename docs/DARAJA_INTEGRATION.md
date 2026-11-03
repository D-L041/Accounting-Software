# Safaricom Daraja integration — staged implementation

## Implemented in this branch

- Authenticated school-scoped STK Push initiation against an issued invoice balance.
- Kenyan MSISDN normalisation and amount rounding to whole KES for STK Push.
- OAuth client-credentials token acquisition and STK Push request construction.
- Persisted STK attempts with unique CheckoutRequestID and callback state.
- STK callback capture followed by Daraja STK Query before attempting a ledger posting.
- Payment posting through the existing billing service, preserving receipt numbering, invoice allocation, double-entry posting and external-reference uniqueness.
- C2B validation and confirmation endpoints. C2B confirmations are durably deduplicated by TransID and held for verification/reconciliation.
- School-scoped C2B review queue that only exposes transactions whose BillRefNumber exactly matches an invoice number in that school.
- Controlled manual reconciliation: an authorised school user must select the invoice and explicitly confirm an independent match against the Safaricom statement. The workflow checks the outstanding invoice balance, duplicate TransID, school/student ownership and financial period through the existing billing service, then creates the normal M-Pesa receipt and balanced ledger journal. The notification stores the linked invoice, payment, operator and reconciliation timestamp.

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

C2B callbacks are captured first and are not automatically posted. The school review queue is available at `GET /api/daraja/schools/{school_id}/c2b/`. Reconcile a selected transaction with `POST /api/daraja/schools/{school_id}/c2b/{notification_id}/reconcile/` using `invoice_id` and `confirm_statement_match: true`. The BillRefNumber must exactly match the selected invoice number and the operator must independently compare the transaction with the Safaricom statement before confirming. Unknown references do not appear in a school queue and must be investigated centrally. Automatic C2B posting remains disabled until Daraja transaction-status verification and school-specific paybill mapping are implemented and independently tested.

## Go-live safety gates

1. Complete Daraja sandbox tests for successful, cancelled, timed-out, duplicate and malformed STK callbacks.
2. Add Daraja transaction-status verification and school-specific paybill mapping before enabling unattended C2B posting. The current controlled workflow requires human statement verification.
3. Verify callback endpoint abuse controls, request-size limits, rate limits, monitoring and retry handling. Daraja callbacks are not authenticated by Django sessions; do not treat an unauthenticated callback body alone as proof of payment.
4. Configure real shortcode, passkey and approved production credentials in the hosting secret manager.
5. Complete Safaricom's production onboarding/go-live process and test a controlled live transaction before school rollout.

No live payment processing should be enabled until the remaining C2B verification, callback security review and production approval gates pass.
