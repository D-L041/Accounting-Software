from django.urls import path

from .views import AccountViewSet, FinancialPeriodViewSet, JournalEntryViewSet

urlpatterns = [
    path("accounts/", AccountViewSet.as_view({"get": "list", "post": "create"}), name="ledger-accounts"),
    path("accounts/<int:pk>/", AccountViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="ledger-account-detail"),
    path("periods/", FinancialPeriodViewSet.as_view({"get": "list", "post": "create"}), name="ledger-periods"),
    path("periods/<int:pk>/", FinancialPeriodViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="ledger-period-detail"),
    path("journals/", JournalEntryViewSet.as_view({"get": "list", "post": "create"}), name="ledger-journals"),
    path("journals/<int:pk>/", JournalEntryViewSet.as_view({"get": "retrieve"}), name="ledger-journal-detail"),
    path("journals/<int:pk>/post/", JournalEntryViewSet.as_view({"post": "post_entry"}), name="ledger-journal-post"),
]
