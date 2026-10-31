from django.contrib import admin

from .models import FeeItem, Invoice, InvoiceLine, Payment, PaymentAllocation, SchoolBillingSettings


@admin.register(FeeItem)
class FeeItemAdmin(admin.ModelAdmin):
    list_display = ["school", "code", "name", "income_account", "is_active"]
    list_filter = ["school", "is_active"]
    search_fields = ["school__name", "code", "name"]


@admin.register(SchoolBillingSettings)
class SchoolBillingSettingsAdmin(admin.ModelAdmin):
    list_display = ["school", "receivables_account", "cash_account", "bank_account"]


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "school", "student", "invoice_date", "due_date", "status"]
    list_filter = ["school", "status", "academic_year"]
    search_fields = ["invoice_number", "student__admission_number", "student__first_name", "student__last_name"]
    inlines = [InvoiceLineInline]
    readonly_fields = ["journal_entry", "created_at"]


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "school", "student", "payment_date", "method", "amount"]
    list_filter = ["school", "method", "payment_date"]
    search_fields = ["receipt_number", "transaction_reference", "student__admission_number"]
    inlines = [PaymentAllocationInline]
    readonly_fields = ["journal_entry", "created_at"]
