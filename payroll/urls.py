from django.urls import path

from .views import EmployeeViewSet, PayrollRuleViewSet, PayrollRunViewSet, PayrollSettingsViewSet, PayrollTaxBandViewSet


urlpatterns = [
    path("rules/", PayrollRuleViewSet.as_view({"get": "list", "post": "create"}), name="payroll-rules"),
    path("rules/<int:pk>/", PayrollRuleViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="payroll-rule-detail"),
    path("tax-bands/", PayrollTaxBandViewSet.as_view({"get": "list", "post": "create"}), name="payroll-tax-bands"),
    path("tax-bands/<int:pk>/", PayrollTaxBandViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="payroll-tax-band-detail"),
    path("employees/", EmployeeViewSet.as_view({"get": "list", "post": "create"}), name="payroll-employees"),
    path("employees/<int:pk>/", EmployeeViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="payroll-employee-detail"),
    path("settings/", PayrollSettingsViewSet.as_view({"get": "list", "post": "create"}), name="payroll-settings"),
    path("settings/<int:pk>/", PayrollSettingsViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="payroll-settings-detail"),
    path("runs/", PayrollRunViewSet.as_view({"get": "list", "post": "create"}), name="payroll-runs"),
    path("runs/<int:pk>/", PayrollRunViewSet.as_view({"get": "retrieve"}), name="payroll-run-detail"),
    path("runs/<int:pk>/post/", PayrollRunViewSet.as_view({"post": "post"}), name="payroll-run-post"),
    path("runs/<int:pk>/statutory-export/", PayrollRunViewSet.as_view({"get": "statutory_export"}), name="payroll-run-statutory-export"),
]
