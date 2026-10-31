# Kenyan payroll statutory review — 31 October 2026

## Scope and conclusion

This is an implementation review against official Kenyan guidance available on 31 October 2026. It is not a legal opinion or a substitute for a payroll professional's sign-off. Payroll must remain a draft/calculation workflow until all employee-specific deductions, reliefs, exemptions and employer obligations below are supported and independently checked.

## Statutory parameters verified

| Item | Current reference point | Implementation status |
|---|---:|---|
| PAYE monthly bands | 10% on first KES 24,000; 25% next KES 8,333; 30% next KES 467,667; 32.5% next KES 300,000; 35% above KES 800,000 | Effective-dated global tax bands seeded |
| Personal relief | KES 2,400 per month for resident individuals | Implemented as an effective-dated rule |
| NSSF from February 2026 | 6% employee and 6% employer; lower earning limit KES 9,000; upper earning limit KES 108,000; maximum KES 6,480 each per month | Effective-dated 6% rate and KES 108,000 ceiling seeded |
| NSSF January 2026 | 6% each up to KES 72,000 (KES 4,320 maximum each) | Separate January effective-dated rule seeded |
| SHIF | 2.75% of gross salary, minimum KES 300 per month; employee contribution | Effective-dated employee rate and minimum seeded |
| Affordable Housing Levy | 1.5% employee and 1.5% employer on gross monthly salary | Effective-dated rates seeded |
| NITA industrial training levy | KES 50 per employee per month, employer-borne and not deducted from salary | Effective-dated flat employer charge calculated and posted to a separate liability account; remittance schedule outstanding |
| PAYE taxable-pay deductions | SHIF and Affordable Housing Levy; NSSF employee pension contribution within the applicable pension deduction limit | NSSF rule corrected by migration 0002; regression test updated |

## Correction made

The original NSSF rule was marked as not deductible for PAYE. KRA's PAYE return guidance identifies NSSF contributions as an allowable pension deduction, subject to the aggregate pension deduction limit. Migration `0002_nssf_paye_deduction` corrects the seeded NSSF rules. The February 2026 payroll regression test now expects the employee NSSF contribution to reduce taxable pay.

## Independent benchmark

For a resident employee with KES 50,000 gross monthly pay and no other claims:

- NSSF employee: KES 3,000
- SHIF: KES 1,375
- Employee Housing Levy: KES 750
- PAYE taxable pay after these deductions: KES 44,875
- PAYE before relief: KES 8,245.85
- Personal relief: KES 2,400
- PAYE: KES 5,845.85
- Net pay: KES 39,029.15

This benchmark is encoded in `payroll/tests.py`. It assumes the stated statutory rates are configured and does not include employee-declared tax claims or non-cash benefits.

## Remaining payroll gaps — release blockers

1. Employee-declared insurance relief (15% of qualifying premiums, subject to the annual limit), mortgage-interest deduction, post-retirement medical fund contributions, and other qualifying pension contributions are not captured.
2. Valid tax exemption certificates and disability-related exemptions are not modelled.
3. Taxable non-cash benefits (including housing, car, low-interest loans and taxable benefits/facilities), meal benefits and other irregular earnings are not fully captured.
4. NITA industrial training levy is now calculated at the effective-dated KES 50 per active employee per month and posted as an employer cost to a separate NITA payable account. The rate, employer-only treatment and remittance timing must still be rechecked for each payroll month; the complete statutory remittance schedule is not yet implemented.
5. Payroll now provides audited CSV exports for the payroll register and PAYE, NSSF, SHIF, Affordable Housing Levy and NITA schedules. Statutory schedules are available only after the payroll run is posted. These are management/remittance working schedules, not KRA P10/iTax upload files or agency-certified remittance files; official formats, PIN/ID validation, SHA/NSSF/NITA portal reconciliation and remittance references still require implementation and review.
6. Independent review by a Kenyan payroll/tax practitioner and parallel-run comparison against authoritative payroll calculations are still required.

Do not use this module to approve or pay live payroll until employee-specific claims and exemptions are implemented, statutory exports are reconciled to the current agency formats, statutory sources are rechecked for the pay period, and a Kenyan payroll practitioner and the school sign off parallel-run results.

## Official sources

- KRA PAYE rates, allowable deductions, personal relief and insurance relief: https://www.kra.go.ke/individual/filing-paying/types-of-taxes/paye
- KRA notice on PAYE computation changes effective 27 December 2024: https://www.kra.go.ke/news-center/public-notices/2157-amendments-to-paye-computation-pursuant-to-the-tax-laws-amendment-act%2C-2024
- KRA guidance on employer obligations for deductions, reliefs and exemptions (6 October 2025): https://www.zd.kra.go.ke/news-center/public-notices/2307-guidance-on-employer-obligations-in-applying-tax-deductions%2C-reliefs-and-exemptions
- KRA simplified PAYE return guide (includes NSSF deduction and KES 30,000 aggregate pension limit): https://www.kra.go.ke/images/publications/STEP-BY-STEP-GUIDE-FOR-THE-SIMPLIFIED-PAYE-RETURN.pdf
- NSSF Year 4 (2026) contribution rates: https://www.nssf.or.ke/notice-to-employers-year-4-2026-nssf-contribution-rates
- Social Health Insurance (General) Regulations, 2024: https://www.health.go.ke/sites/default/files/2024-11/Social%20Health%20Insurance%20%28General%29%20Regulations%2C%202024_0.pdf
- NITA levy guidance (KES 50 per employee per month; employer cost, not deducted from payroll): https://www.nita.go.ke/faq-s/99-nita-services
- Industrial Training (Amendment) Act, 2022 (section 5B: employer-borne levy and collection): https://resources.mwakili.com/resources/legal-docs-plain-text/TheIndustrialTraining_Amendment_Act_2022
- NITA levy forms and remittance returns: https://www.nita.go.ke/media-centre/downloads/industrial-training-levy.html
