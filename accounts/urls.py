from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AcademicYearViewSet, ClassRoomViewSet, SchoolViewSet, StudentViewSet
from .auth_views import CsrfView, CurrentUserView, LoginView, LogoutView
from .member_views import SchoolMemberDetailView, SchoolMemberListCreateView

router = DefaultRouter()
router.register("schools", SchoolViewSet, basename="school")

school_patterns = [
    path("members/", SchoolMemberListCreateView.as_view(), name="school-members"),
    path("members/<int:pk>/", SchoolMemberDetailView.as_view(), name="school-member-detail"),
    path("academic-years/", AcademicYearViewSet.as_view({"get": "list", "post": "create"}), name="school-academic-years"),
    path("academic-years/<int:pk>/", AcademicYearViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="school-academic-year-detail"),
    path("classrooms/", ClassRoomViewSet.as_view({"get": "list", "post": "create"}), name="school-classrooms"),
    path("classrooms/<int:pk>/", ClassRoomViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="school-classroom-detail"),
    path("students/", StudentViewSet.as_view({"get": "list", "post": "create"}), name="school-students"),
    path("students/<int:pk>/", StudentViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="school-student-detail"),
]

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-me"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("", include(router.urls)),
    path("schools/<int:school_pk>/", include((school_patterns, "school-scoped"))),
]
