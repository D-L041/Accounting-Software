from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from billing.models import Payment, SchoolBillingSettings
from ledger.models import JournalEntry, JournalLine

from .models import Expense


@transaction.atomic
def post_expense(expense_id, user):
    expense = Expense.objects.select_for_update().select_related(
        "school", "category__expense_account", "period", "supplier"
    ).select_for_update(of=("self",)).get(pk=expense_id)
    if expense.status != Expense.Status.DRAFT:
        raise ValidationError("Only draft expenses can be posted.")
    if expense.period.is_locked:
        raise ValidationError("Cannot post an expense into a locked financial period.")
    if not (expense.period.starts_on <= expense.expense_date <= expense.period.ends_on):
        raise ValidationError("Expense date must fall within its financial period.")
    settings = SchoolBillingSettings.objects.filter(school=expense.school).first()
    if settings is None:
        raise ValidationError("Configure school billing cash, bank and M-Pesa accounts before posting expenses.")
    payment_account = (
        settings.bank_account if expense.payment_method == Payment.Method.BANK
        else settings.mpesa_account if expense.payment_method == Payment.Method.MPESA
        else settings.cash_account
    )
    journal = JournalEntry.objects.create(
        school=expense.school, reference=f"EXP-{expense.expense_number}",
        description=f"Expense {expense.expense_number}: {expense.description}",
        entry_date=expense.expense_date, period=expense.period, created_by=user,
    )
    JournalLine.objects.create(
        entry=journal, account=expense.category.expense_account,
        description=expense.description, debit=expense.amount,
    )
    JournalLine.objects.create(
        entry=journal, account=payment_account,
        description=f"Paid by {expense.get_payment_method_display()}", credit=expense.amount,
    )
    journal.post()
    expense.journal_entry = journal
    expense.status = Expense.Status.POSTED
    expense.save(update_fields=["journal_entry", "status"])
    return expense
