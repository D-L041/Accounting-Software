from django.urls import path

from .views import SchoolAuditEventListView

urlpatterns = [
    path("", SchoolAuditEventListView.as_view(), name="school-audit-events"),
]
