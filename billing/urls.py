from django.urls import path

from .views import BillingSettingsViewSet, FeeItemViewSet, FeeScheduleViewSet, InvoiceViewSet, PaymentViewSet
from .receipt_views import PaymentReceiptPdfView

urlpatterns = [
    path("fee-schedules/", FeeScheduleViewSet.as_view({"get": "list", "post": "create"}), name="billing-fee-schedules"),
    path("fee-schedules/<int:pk>/", FeeScheduleViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="billing-fee-schedule-detail"),
    path("fee-schedules/<int:pk>/generate-invoices/", FeeScheduleViewSet.as_view({"post": "generate_invoices"}), name="billing-fee-schedule-generate-invoices"),
    path("fee-items/", FeeItemViewSet.as_view({"get": "list", "post": "create"}), name="billing-fee-items"),
    path("fee-items/<int:pk>/", FeeItemViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="billing-fee-item-detail"),
    path("settings/", BillingSettingsViewSet.as_view({"get": "list", "post": "create"}), name="billing-settings"),
    path("settings/<int:pk>/", BillingSettingsViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update"}), name="billing-settings-detail"),
    path("invoices/", InvoiceViewSet.as_view({"get": "list", "post": "create"}), name="billing-invoices"),
    path("invoices/<int:pk>/", InvoiceViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="billing-invoice-detail"),
    path("invoices/<int:pk>/issue/", InvoiceViewSet.as_view({"post": "issue"}), name="billing-invoice-issue"),
    path("payments/", PaymentViewSet.as_view({"get": "list", "post": "create"}), name="billing-payments"),
    path("payments/<int:pk>/receipt/", PaymentReceiptPdfView.as_view(), name="billing-payment-receipt"),
    path("payments/<int:pk>/", PaymentViewSet.as_view({"get": "retrieve"}), name="billing-payment-detail"),
]
