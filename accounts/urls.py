from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AcademicYearViewSet, ClassRoomViewSet, SchoolViewSet, StudentViewSet

router = DefaultRouter()
router.register("schools", SchoolViewSet, basename="school")

school_patterns = [
    path("academic-years/", AcademicYearViewSet.as_view({"get": "list", "post": "create"}), name="school-academic-years"),
    path("academic-years/<int:pk>/", AcademicYearViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="school-academic-year-detail"),
    path("classrooms/", ClassRoomViewSet.as_view({"get": "list", "post": "create"}), name="school-classrooms"),
    path("classrooms/<int:pk>/", ClassRoomViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="school-classroom-detail"),
    path("students/", StudentViewSet.as_view({"get": "list", "post": "create"}), name="school-students"),
    path("students/<int:pk>/", StudentViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="school-student-detail"),
]

urlpatterns = [
    path("auth/csrf/", __import__("accounts.auth_views", fromlist=["CsrfView"]).CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", __import__("accounts.auth_views", fromlist=["LoginView"]).LoginView.as_view(), name="auth-login"),
    path("auth/me/", __import__("accounts.auth_views", fromlist=["CurrentUserView"]).CurrentUserView.as_view(), name="auth-me"),
    path("auth/logout/", __import__("accounts.auth_views", fromlist=["LogoutView"]).LogoutView.as_view(), name="auth-logout"),
    path("", include(router.urls)),
    path("schools/<int:school_pk>/", include((school_patterns, "school-scoped"))),
]
