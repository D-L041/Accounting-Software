from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/schools/<int:school_pk>/ledger/", include("ledger.urls")),
    path("api/schools/<int:school_pk>/billing/", include("billing.urls")),
    path("api/schools/<int:school_pk>/expenses/", include("expenses.urls")),
    path("api/schools/<int:school_pk>/audit/", include("auditlog.urls")),
]
