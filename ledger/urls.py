from django.urls import path

from .views import AccountViewSet, BankStatementViewSet, FinancialPeriodViewSet, JournalEntryViewSet
from .report_views import BalanceSheetView, CashbookView, CashFlowView, IncomeExpenditureView, TrialBalanceView

urlpatterns = [
    path("reports/cashbook/", CashbookView.as_view(), name="ledger-cashbook"),
    path("reports/cash-flow/", CashFlowView.as_view(), name="ledger-cash-flow"),
    path("reports/trial-balance/", TrialBalanceView.as_view(), name="ledger-trial-balance"),
    path("reports/income-expenditure/", IncomeExpenditureView.as_view(), name="ledger-income-expenditure"),
    path("reports/balance-sheet/", BalanceSheetView.as_view(), name="ledger-balance-sheet"),
    path("bank-statements/", BankStatementViewSet.as_view({"get": "list", "post": "create"}), name="ledger-bank-statements"),
    path("bank-statements/<int:pk>/", BankStatementViewSet.as_view({"get": "retrieve"}), name="ledger-bank-statement-detail"),
    path("bank-statements/<int:pk>/match-line/", BankStatementViewSet.as_view({"post": "match_line"}), name="ledger-bank-statement-match-line"),
    path("bank-statements/<int:pk>/reconcile/", BankStatementViewSet.as_view({"post": "reconcile"}), name="ledger-bank-statement-reconcile"),
    path("accounts/", AccountViewSet.as_view({"get": "list", "post": "create"}), name="ledger-accounts"),
    path("accounts/<int:pk>/", AccountViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="ledger-account-detail"),
    path("periods/", FinancialPeriodViewSet.as_view({"get": "list", "post": "create"}), name="ledger-periods"),
    path("periods/<int:pk>/", FinancialPeriodViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="ledger-period-detail"),
    path("periods/<int:pk>/lock/", FinancialPeriodViewSet.as_view({"post": "lock_period"}), name="ledger-period-lock"),
    path("journals/", JournalEntryViewSet.as_view({"get": "list", "post": "create"}), name="ledger-journals"),
    path("journals/<int:pk>/", JournalEntryViewSet.as_view({"get": "retrieve"}), name="ledger-journal-detail"),
    path("journals/<int:pk>/post/", JournalEntryViewSet.as_view({"post": "post_entry"}), name="ledger-journal-post"),
]
