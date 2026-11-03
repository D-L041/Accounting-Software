from django.contrib import admin

from .models import AcademicYear, ClassRoom, School, SchoolMembership, Student


class SchoolMembershipInline(admin.TabularInline):
    model = SchoolMembership
    extra = 0


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "currency", "is_active", "created_at"]
    search_fields = ["name", "code", "email"]
    inlines = [SchoolMembershipInline]


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ["school", "name", "starts_on", "ends_on", "is_current"]
    list_filter = ["school", "is_current"]


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ["school", "academic_year", "name", "stream", "is_active"]
    list_filter = ["school", "academic_year", "is_active"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["admission_number", "full_name", "school", "classroom", "status"]
    list_filter = ["school", "status", "classroom"]
    search_fields = ["admission_number", "first_name", "middle_name", "last_name", "guardian_name", "guardian_phone"]
    readonly_fields = ["created_at", "updated_at"]
