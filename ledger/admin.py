from django.contrib import admin

from .models import Account, FinancialPeriod, JournalEntry, JournalLine


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["school", "code", "name", "category", "is_active"]
    list_filter = ["school", "category", "is_active"]
    search_fields = ["school__name", "code", "name"]


@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(admin.ModelAdmin):
    list_display = ["school", "name", "starts_on", "ends_on", "is_locked"]
    list_filter = ["school", "is_locked"]


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.posted:
            return [field.name for field in self.model._meta.fields]
        return []

    def has_add_permission(self, request, obj=None):
        return not (obj and obj.posted)

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.posted)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["school", "reference", "entry_date", "period", "posted", "posted_at"]
    list_filter = ["school", "period", "posted"]
    search_fields = ["reference", "description", "school__name"]
    readonly_fields = ["posted_at", "created_at"]
    inlines = [JournalLineInline]

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.posted:
            fields.extend(["school", "reference", "description", "entry_date", "period", "posted", "created_by"])
        return fields

    def has_delete_permission(self, request, obj=None):
        if obj and obj.posted:
            return False
        return super().has_delete_permission(request, obj)
