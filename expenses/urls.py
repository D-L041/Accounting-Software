from django.urls import path

from .views import ExpenseCategoryViewSet, ExpenseViewSet, SupplierViewSet

urlpatterns = [
    path("suppliers/", SupplierViewSet.as_view({"get": "list", "post": "create"}), name="expense-suppliers"),
    path("suppliers/<int:pk>/", SupplierViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="expense-supplier-detail"),
    path("categories/", ExpenseCategoryViewSet.as_view({"get": "list", "post": "create"}), name="expense-categories"),
    path("categories/<int:pk>/", ExpenseCategoryViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="expense-category-detail"),
    path("expenses/", ExpenseViewSet.as_view({"get": "list", "post": "create"}), name="expenses"),
    path("expenses/<int:pk>/", ExpenseViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="expense-detail"),
    path("expenses/<int:pk>/post/", ExpenseViewSet.as_view({"post": "post_expense"}), name="expense-post"),
]
