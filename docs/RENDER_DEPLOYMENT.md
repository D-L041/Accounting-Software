# Render hosting recommendation — Precious SchoolBooks

## Recommended pilot architecture

Use one Render Docker web service to serve both the built React application and Django API from the **same HTTPS origin**, with a separate managed Render PostgreSQL database in the same Frankfurt region. This avoids cross-site session-cookie problems while there is no custom domain and keeps the existing Django session/CSRF authentication model intact. The frontend build is included in the API Docker image; WhiteNoise serves the hashed static assets and Django serves the PWA shell, manifest and service worker.

The infrastructure definition is in the repository root as `render.yaml`. It is a blueprint only; no Render resources have been created and no billing has been activated.

## Pilot resource estimate

| Resource | Pilot size | Published monthly price |
|---|---:|---:|
| Render web service | 0.5 CPU / 512 MB | US$7 |
| Render PostgreSQL | 256 MB plan | US$10 |
| Render Hobby workspace | 1 member | US$0 |
| Custom domain | Not required | US$0 |
| **Estimated base total** | | **US$17/month** |

Prices checked against Render's published pricing on 31 October 2026. They exclude taxes, additional bandwidth, storage growth and any upgrades. Confirm the live price in Render before creating the Blueprint. The 256 MB database is a small pilot size only; upgrade to at least the 1 GB database tier and establish independent backups before real school financial data is loaded. Render's Hobby workspace database point-in-time recovery window is limited; do not rely on the hosting plan alone as the only backup.

## Why not split the frontend and API yet?

The current application uses Django session authentication and CSRF protection. With no custom domain, separate provider hostnames would be cross-site and can be affected by browser third-party-cookie restrictions. A single origin is the safer initial arrangement. A later split can be reconsidered after a custom domain and a reviewed authentication architecture are available.

Vercel Hobby is not appropriate for this commercial school accounting service: Vercel describes Hobby as intended for personal, non-commercial use. A paid plan would add cost without solving the same-origin issue by itself.

## Before a first hosted acceptance environment

1. The repository owner must connect the GitHub repository to Render and review the Blueprint's resource sizes and billing.
2. Confirm the service name is available. If it must change, update `ALLOWED_HOSTS` and the Daraja callback URL before sandbox testing.
3. Keep auto-deploy disabled. Deploy only a reviewed commit after the CI and release gates pass.
4. Set Daraja sandbox credentials privately in Render's secret manager; never commit them or paste them into chat.
5. Configure database backup retention and test restoration before loading any real data.
6. Use synthetic St Stephen School acceptance data first. Do not onboard live pupil, employee, parent or financial data until security, privacy and acceptance sign-off is complete.

## Provider references

- Render pricing: https://render.com/pricing
- Render Blueprint reference: https://render.com/docs/blueprint-spec
- Render PostgreSQL: https://render.com/docs/databases
- Vercel plans and Hobby non-commercial limitation: https://vercel.com/pricing

**Deployment status:** Not provisioned. No domain has been purchased. This file prepares the deployment; it does not create services or incur charges.
