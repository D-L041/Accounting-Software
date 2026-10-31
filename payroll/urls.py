from django.urls import path

from .views import EmployeeViewSet, PayrollRunViewSet, PayrollSettingsViewSet


urlpatterns = [
    path("employees/", EmployeeViewSet.as_view({"get": "list", "post": "create"}), name="payroll-employees"),
    path("employees/<int:pk>/", EmployeeViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="payroll-employee-detail"),
    path("settings/", PayrollSettingsViewSet.as_view({"get": "list", "post": "create"}), name="payroll-settings"),
    path("settings/<int:pk>/", PayrollSettingsViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="payroll-settings-detail"),
    path("runs/", PayrollRunViewSet.as_view({"get": "list", "post": "create"}), name="payroll-runs"),
    path("runs/<int:pk>/", PayrollRunViewSet.as_view({"get": "retrieve"}), name="payroll-run-detail"),
    path("runs/<int:pk>/post/", PayrollRunViewSet.as_view({"post": "post"}), name="payroll-run-post"),
]
