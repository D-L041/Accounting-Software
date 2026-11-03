from decimal import Decimal

from django.db.models import Sum

from .models import JournalLine


def build_trial_balance(period):
    """Return posted ledger totals for one financial period.

    Opening balances are not inferred; they must be posted explicitly.
    """
    rows = (
        JournalLine.objects.filter(entry__period=period, entry__posted=True)
        .values("account_id", "account__code", "account__name", "account__category")
        .annotate(debits=Sum("debit"), credits=Sum("credit"))
        .order_by("account__code")
    )
    accounts = []
    total_debits = Decimal("0.00")
    total_credits = Decimal("0.00")
    for row in rows:
        debits = row["debits"] or Decimal("0.00")
        credits = row["credits"] or Decimal("0.00")
        total_debits += debits
        total_credits += credits
        accounts.append({
            "account_id": row["account_id"],
            "code": row["account__code"],
            "name": row["account__name"],
            "category": row["account__category"],
            "debits": debits,
            "credits": credits,
            "net_debit": max(debits - credits, Decimal("0.00")),
            "net_credit": max(credits - debits, Decimal("0.00")),
        })
    return {
        "period": period.name,
        "accounts": accounts,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "difference": total_debits - total_credits,
        "is_balanced": total_debits == total_credits,
    }



def build_income_expenditure_statement(period):
    rows = (
        JournalLine.objects.filter(
            entry__school=period.school,
            entry__posted=True,
            entry__entry_date__gte=period.starts_on,
            entry__entry_date__lte=period.ends_on,
            account__category__in=["INCOME", "EXPENSE"],
        )
        .values("account_id", "account__code", "account__name", "account__category")
        .annotate(debits=Sum("debit"), credits=Sum("credit"))
        .order_by("account__code")
    )
    income = []
    expenditure = []
    total_income = Decimal("0.00")
    total_expenditure = Decimal("0.00")
    for row in rows:
        debits = row["debits"] or Decimal("0.00")
        credits = row["credits"] or Decimal("0.00")
        amount = credits - debits if row["account__category"] == "INCOME" else debits - credits
        item = {"account_id": row["account_id"], "code": row["account__code"], "name": row["account__name"], "amount": amount}
        if row["account__category"] == "INCOME":
            income.append(item)
            total_income += amount
        else:
            expenditure.append(item)
            total_expenditure += amount
    return {
        "period": period.name,
        "starts_on": period.starts_on,
        "ends_on": period.ends_on,
        "income": income,
        "expenditure": expenditure,
        "total_income": total_income,
        "total_expenditure": total_expenditure,
        "surplus_deficit": total_income - total_expenditure,
    }


def build_balance_sheet(period):
    rows = (
        JournalLine.objects.filter(
            entry__school=period.school,
            entry__posted=True,
            entry__entry_date__lte=period.ends_on,
            account__category__in=["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"],
        )
        .values("account_id", "account__code", "account__name", "account__category")
        .annotate(debits=Sum("debit"), credits=Sum("credit"))
        .order_by("account__code")
    )
    sections = {"ASSET": [], "LIABILITY": [], "EQUITY": []}
    totals = {"ASSET": Decimal("0.00"), "LIABILITY": Decimal("0.00"), "EQUITY": Decimal("0.00")}
    income_total = Decimal("0.00")
    expense_total = Decimal("0.00")
    for row in rows:
        debits = row["debits"] or Decimal("0.00")
        credits = row["credits"] or Decimal("0.00")
        category = row["account__category"]
        if category == "ASSET":
            amount = debits - credits
            sections[category].append({"account_id": row["account_id"], "code": row["account__code"], "name": row["account__name"], "amount": amount})
            totals[category] += amount
        elif category in {"LIABILITY", "EQUITY"}:
            amount = credits - debits
            sections[category].append({"account_id": row["account_id"], "code": row["account__code"], "name": row["account__name"], "amount": amount})
            totals[category] += amount
        elif category == "INCOME":
            income_total += credits - debits
        elif category == "EXPENSE":
            expense_total += debits - credits
    retained_surplus = income_total - expense_total
    liabilities_and_equity = totals["LIABILITY"] + totals["EQUITY"] + retained_surplus
    return {
        "as_at": period.ends_on,
        "assets": sections["ASSET"],
        "liabilities": sections["LIABILITY"],
        "equity": sections["EQUITY"],
        "total_assets": totals["ASSET"],
        "total_liabilities": totals["LIABILITY"],
        "total_equity": totals["EQUITY"],
        "retained_surplus_deficit": retained_surplus,
        "total_liabilities_and_equity": liabilities_and_equity,
        "difference": totals["ASSET"] - liabilities_and_equity,
        "is_balanced": totals["ASSET"] == liabilities_and_equity,
    }


def build_cashbook(period):
    """Return posted cash, bank and M-Pesa movements with ledger-derived opening balances."""
    from billing.models import SchoolBillingSettings

    settings = SchoolBillingSettings.objects.filter(school=period.school).first()
    zero = Decimal("0.00")
    if settings is None:
        return {
            "period": period.name,
            "transactions": [],
            "total_receipts": zero,
            "total_payments": zero,
            "net_movement": zero,
            "opening_balance_total": zero,
            "closing_balance_total": zero,
            "opening_balances": [],
            "closing_balances": [],
            "opening_balance_included": False,
        }

    account_ids = list(dict.fromkeys([
        settings.cash_account_id,
        settings.bank_account_id,
        settings.mpesa_account_id,
    ]))
    opening_lines = (
        JournalLine.objects.filter(
            entry__school=period.school,
            entry__posted=True,
            entry__entry_date__lt=period.starts_on,
            account_id__in=account_ids,
        )
        .select_related("account")
        .order_by("entry__entry_date", "entry_id", "id")
    )
    balances = {account_id: zero for account_id in account_ids}
    accounts = {}
    for line in opening_lines:
        balances[line.account_id] += line.debit - line.credit
        accounts[line.account_id] = line.account

    for account_id in account_ids:
        accounts.setdefault(
            account_id,
            next(
                account for account in (
                    settings.cash_account, settings.bank_account, settings.mpesa_account
                ) if account.pk == account_id
            ),
        )

    opening_balances = [
        {
            "account_id": account_id,
            "account_code": accounts[account_id].code,
            "account_name": accounts[account_id].name,
            "balance": balances[account_id],
        }
        for account_id in account_ids
    ]
    opening_balance_total = sum(balances.values(), zero)

    lines = (
        JournalLine.objects.filter(
            entry__school=period.school,
            entry__period=period,
            entry__posted=True,
            account_id__in=account_ids,
        )
        .select_related("entry", "account")
        .order_by("entry__entry_date", "entry_id", "id")
    )
    transactions = []
    total_receipts = zero
    total_payments = zero
    for line in lines:
        balances[line.account_id] += line.debit - line.credit
        total_receipts += line.debit
        total_payments += line.credit
        transactions.append({
            "date": line.entry.entry_date,
            "journal_reference": line.entry.reference,
            "description": line.description or line.entry.description,
            "account_id": line.account_id,
            "account_code": line.account.code,
            "account_name": line.account.name,
            "debit": line.debit,
            "credit": line.credit,
            "movement_balance": balances[line.account_id],
        })

    closing_balances = [
        {
            "account_id": account_id,
            "account_code": accounts[account_id].code,
            "account_name": accounts[account_id].name,
            "balance": balances[account_id],
        }
        for account_id in account_ids
    ]
    return {
        "period": period.name,
        "transactions": transactions,
        "total_receipts": total_receipts,
        "total_payments": total_payments,
        "net_movement": total_receipts - total_payments,
        "opening_balance_total": opening_balance_total,
        "closing_balance_total": sum(balances.values(), zero),
        "opening_balances": opening_balances,
        "closing_balances": closing_balances,
        "opening_balance_included": True,
    }
