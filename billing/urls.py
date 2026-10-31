from django.urls import path

from .views import BillingSettingsViewSet, FeeItemViewSet, InvoiceViewSet, PaymentViewSet

urlpatterns = [
    path("fee-items/", FeeItemViewSet.as_view({"get": "list", "post": "create"}), name="billing-fee-items"),
    path("fee-items/<int:pk>/", FeeItemViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="billing-fee-item-detail"),
    path("settings/", BillingSettingsViewSet.as_view({"get": "list", "post": "create"}), name="billing-settings"),
    path("settings/<int:pk>/", BillingSettingsViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update"}), name="billing-settings-detail"),
    path("invoices/", InvoiceViewSet.as_view({"get": "list", "post": "create"}), name="billing-invoices"),
    path("invoices/<int:pk>/", InvoiceViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="billing-invoice-detail"),
    path("invoices/<int:pk>/issue/", InvoiceViewSet.as_view({"post": "issue"}), name="billing-invoice-issue"),
    path("payments/", PaymentViewSet.as_view({"get": "list", "post": "create"}), name="billing-payments"),
    path("payments/<int:pk>/", PaymentViewSet.as_view({"get": "retrieve"}), name="billing-payment-detail"),
]
