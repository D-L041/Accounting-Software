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
