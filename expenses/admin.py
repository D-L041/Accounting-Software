from django.contrib import admin

from .models import Expense, ExpenseCategory, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["school", "name", "contact_person", "phone", "tax_pin", "is_active"]
    list_filter = ["school", "is_active"]
    search_fields = ["school__name", "name", "phone", "tax_pin"]


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ["school", "code", "name", "expense_account", "is_active"]
    list_filter = ["school", "is_active"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["expense_number", "school", "expense_date", "supplier", "category", "amount", "payment_method", "status"]
    list_filter = ["school", "category", "payment_method", "status"]
    search_fields = ["expense_number", "description", "reference", "supplier__name"]
    readonly_fields = ["journal_entry", "created_at"]
