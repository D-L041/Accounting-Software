from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from auditlog.services import record_event
from ledger.models import FinancialPeriod, JournalEntry, JournalLine

from .models import Employee, PayrollLine, PayrollRule, PayrollRun, PayrollSettings, PayrollTaxBand


CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def effective_rule(school, code, payroll_month):
    active = PayrollRule.objects.filter(
        code=code, effective_from__lte=payroll_month
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=payroll_month))
    return (
        active.filter(school=school).order_by("-effective_from").first()
        or active.filter(school__isnull=True).order_by("-effective_from").first()
    )


def tax_bands(school, payroll_month):
    active = PayrollTaxBand.objects.filter(
        effective_from__lte=payroll_month
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=payroll_month))
    school_bands = list(active.filter(school=school).order_by("lower_bound"))
    return school_bands or list(active.filter(school__isnull=True).order_by("lower_bound"))


def calculate_paye(taxable_pay, bands, relief):
    tax = Decimal("0.00")
    for band in bands:
        if taxable_pay <= band.lower_bound:
            continue
        upper = band.upper_bound if band.upper_bound is not None else taxable_pay
        taxable_in_band = max(Decimal("0.00"), min(taxable_pay, upper) - band.lower_bound)
        tax += taxable_in_band * band.rate
    return money(max(Decimal("0.00"), tax - relief))


@transaction.atomic
def create_payroll_run(*, school, period, payroll_month, pay_date, user):
    from accounts.models import School as SchoolModel
    SchoolModel.objects.select_for_update().get(pk=school.pk)
    if period.school_id != school.id:
        raise ValidationError("Financial period must belong to this school.")
    if period.is_locked:
        raise ValidationError("Cannot create payroll in a locked financial period.")
    if payroll_month.day != 1:
        raise ValidationError("Payroll month must be the first day of the month.")
    period_start = FinancialPeriod._meta.get_field("starts_on").to_python(period.starts_on)
    period_end = FinancialPeriod._meta.get_field("ends_on").to_python(period.ends_on)
    if not (period_start <= payroll_month <= period_end):
        raise ValidationError("Payroll month must fall within the selected financial period.")
    if not (period_start <= pay_date <= period_end):
        raise ValidationError("Pay date must fall within the selected financial period.")
    if PayrollRun.objects.filter(school=school, payroll_month=payroll_month).exists():
        raise ValidationError("A payroll run already exists for this school and month.")
    employees = list(Employee.objects.filter(school=school, is_active=True).order_by("id"))
    if not employees:
        raise ValidationError("Add at least one active employee before creating payroll.")
    rules = {
        code: effective_rule(school, code, payroll_month)
        for code in PayrollRule.Code.values
    }
    missing = [code for code, rule in rules.items() if rule is None]
    if missing:
        raise ValidationError(f"Missing effective statutory payroll rules: {', '.join(missing)}.")
    bands = tax_bands(school, payroll_month)
    if not bands:
        raise ValidationError("No effective PAYE tax bands are configured for this month.")
    run = PayrollRun.objects.create(
        school=school, period=period, payroll_month=payroll_month,
        pay_date=pay_date, created_by=user,
    )
    for employee in employees:
        gross = money(employee.basic_salary + employee.regular_cash_allowances)
        nssf_base = min(gross, rules["NSSF"].ceiling) if rules["NSSF"].ceiling else gross
        nssf_employee = money(nssf_base * rules["NSSF"].employee_rate)
        nssf_employer = money(nssf_base * rules["NSSF"].employer_rate)
        shif_employee = max(
            money(gross * rules["SHIF"].employee_rate),
            money(rules["SHIF"].minimum_employee),
        )
        housing_employee = money(gross * rules["HOUSING_LEVY"].employee_rate)
        housing_employer = money(gross * rules["HOUSING_LEVY"].employer_rate)
        taxable = gross
        for code, deduction in (
            ("NSSF", nssf_employee),
            ("SHIF", shif_employee),
            ("HOUSING_LEVY", housing_employee),
        ):
            if rules[code].deductible_for_paye:
                taxable -= deduction
        taxable = max(Decimal("0.00"), taxable)
        relief = rules["PERSONAL_RELIEF"].fixed_employee if employee.is_resident else Decimal("0.00")
        paye = calculate_paye(taxable, bands, relief)
        other_deductions = money(employee.monthly_other_deductions)
        net = money(gross - paye - nssf_employee - shif_employee - housing_employee - other_deductions)
        if net < 0:
            raise ValidationError(f"Statutory deductions exceed gross pay for employee {employee.employee_number}.")
        PayrollLine.objects.create(
            run=run, employee=employee, basic_salary=employee.basic_salary,
            other_earnings=employee.regular_cash_allowances, gross_pay=gross, taxable_pay=money(taxable),
            paye=paye, nssf_employee=nssf_employee, shif_employee=shif_employee,
            housing_levy_employee=housing_employee, other_deductions=other_deductions, net_pay=net,
            nssf_employer=nssf_employer, housing_levy_employer=housing_employer,
        )
    record_event(
        school=school, actor=user, action="PAYROLL_RUN_CREATED",
        entity_type="PayrollRun", entity_id=run.pk,
        summary=f"Created draft payroll for {payroll_month:%B %Y}",
        metadata={"employee_count": len(employees), "gross_total": str(run.gross_total)},
    )
    return run


@transaction.atomic
def post_payroll_run(run_id, user):
    run = PayrollRun.objects.select_for_update().select_related("school", "period").get(pk=run_id)
    if run.status != PayrollRun.Status.DRAFT:
        raise ValidationError("Only draft payroll runs can be posted.")
    if run.period.is_locked:
        raise ValidationError("Cannot post payroll into a locked financial period.")
    settings = PayrollSettings.objects.filter(school=run.school).first()
    if settings is None:
        raise ValidationError("Configure payroll expense and statutory payable accounts before posting payroll.")
    lines = list(run.lines.all())
    if not lines:
        raise ValidationError("Payroll run has no employee lines.")
    gross = sum((line.gross_pay for line in lines), Decimal("0.00"))
    net = sum((line.net_pay for line in lines), Decimal("0.00"))
    paye = sum((line.paye for line in lines), Decimal("0.00"))
    nssf = sum((line.nssf_employee + line.nssf_employer for line in lines), Decimal("0.00"))
    shif = sum((line.shif_employee for line in lines), Decimal("0.00"))
    housing = sum((line.housing_levy_employee + line.housing_levy_employer for line in lines), Decimal("0.00"))
    other_deductions = sum((line.other_deductions for line in lines), Decimal("0.00"))
    employer_cost = sum((line.nssf_employer + line.housing_levy_employer for line in lines), Decimal("0.00"))
    journal = JournalEntry.objects.create(
        school=run.school, reference=f"PAY-{run.payroll_month:%Y%m}",
        description=f"Payroll for {run.payroll_month:%B %Y}",
        entry_date=run.pay_date, period=run.period, created_by=user,
    )
    JournalLine.objects.create(
        entry=journal, account=settings.salary_expense_account,
        description="Gross salaries and employer statutory contributions",
        debit=gross + employer_cost,
    )
    credits = [
        (settings.net_payable_account, net, "Net salaries payable"),
        (settings.paye_payable_account, paye, "PAYE payable"),
        (settings.nssf_payable_account, nssf, "Employee and employer NSSF payable"),
        (settings.shif_payable_account, shif, "SHIF payable"),
        (settings.housing_levy_payable_account, housing, "Employee and employer housing levy payable"),
        (settings.other_deductions_payable_account, other_deductions, "Other employee deductions payable"),
    ]
    for account, amount, description in credits:
        if amount > 0:
            JournalLine.objects.create(entry=journal, account=account, description=description, credit=amount)
    journal.post(actor=user)
    run.journal_entry = journal
    run.status = PayrollRun.Status.POSTED
    run.save(update_fields=["journal_entry", "status"])
    record_event(
        school=run.school, actor=user, action="PAYROLL_RUN_POSTED",
        entity_type="PayrollRun", entity_id=run.pk,
        summary=f"Posted payroll for {run.payroll_month:%B %Y}",
        metadata={"gross_total": str(gross), "net_total": str(net), "journal_entry_id": journal.pk},
    )
    return run
