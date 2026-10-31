from django.contrib import admin
from django.urls import include, path
from config.health_views import HealthCheckView

urlpatterns = [
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/daraja/", include("daraja.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/schools/<int:school_pk>/ledger/", include("ledger.urls")),
    path("api/schools/<int:school_pk>/billing/", include("billing.urls")),
    path("api/schools/<int:school_pk>/expenses/", include("expenses.urls")),
    path("api/schools/<int:school_pk>/payroll/", include("payroll.urls")),
    path("api/schools/<int:school_pk>/audit/", include("auditlog.urls")),
]
