from django.contrib import admin
from django.urls import include, path
from config.health_views import HealthCheckView
from config.frontend_views import frontend_index, frontend_public_asset

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
    # Same-origin SPA hosting keeps session and CSRF cookies first-party.
    path("manifest.webmanifest", frontend_public_asset, {"filename": "manifest.webmanifest"}, name="frontend-manifest"),
    path("icon.svg", frontend_public_asset, {"filename": "icon.svg"}, name="frontend-icon"),
    path("sw.js", frontend_public_asset, {"filename": "sw.js"}, name="frontend-service-worker"),
    path("index.html", frontend_index, name="frontend-index"),
    path("", frontend_index, name="frontend-home"),
]
