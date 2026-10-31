from django.urls import path

from .views import ExpenseBudgetViewSet, ExpenseCategoryViewSet, ExpenseViewSet, SupplierViewSet, SupplierBillViewSet, PurchaseOrderViewSet, ProcurementApprovalRuleViewSet

urlpatterns = [
    path("purchase-orders/", PurchaseOrderViewSet.as_view({"get": "list", "post": "create"}), name="purchase-orders"),
    path("purchase-orders/<int:pk>/", PurchaseOrderViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="purchase-order-detail"),
    path("purchase-orders/<int:pk>/submit/", PurchaseOrderViewSet.as_view({"post": "submit"}), name="purchase-order-submit"),
    path("purchase-orders/<int:pk>/approve/", PurchaseOrderViewSet.as_view({"post": "approve"}), name="purchase-order-approve"),
    path("procurement-approval-rules/", ProcurementApprovalRuleViewSet.as_view({"get": "list", "post": "create"}), name="procurement-approval-rules"),
    path("procurement-approval-rules/<int:pk>/", ProcurementApprovalRuleViewSet.as_view({"patch": "partial_update", "delete": "destroy"}), name="procurement-approval-rule-detail"),
    path("budgets/", ExpenseBudgetViewSet.as_view({"get": "list", "post": "create"}), name="expense-budgets"),
    path("budgets/<int:pk>/", ExpenseBudgetViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="expense-budget-detail"),
    path("bills/", SupplierBillViewSet.as_view({"get": "list", "post": "create"}), name="supplier-bills"),
    path("bills/<int:pk>/", SupplierBillViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="supplier-bill-detail"),
    path("bills/<int:pk>/submit/", SupplierBillViewSet.as_view({"post": "submit"}), name="supplier-bill-submit"),
    path("bills/<int:pk>/approve/", SupplierBillViewSet.as_view({"post": "approve"}), name="supplier-bill-approve"),
    path("bills/<int:pk>/post/", SupplierBillViewSet.as_view({"post": "post_bill"}), name="supplier-bill-post"),
    path("bills/<int:pk>/payments/", SupplierBillViewSet.as_view({"post": "record_payment"}), name="supplier-bill-payment"),
    path("suppliers/", SupplierViewSet.as_view({"get": "list", "post": "create"}), name="expense-suppliers"),
    path("suppliers/<int:pk>/", SupplierViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="expense-supplier-detail"),
    path("categories/", ExpenseCategoryViewSet.as_view({"get": "list", "post": "create"}), name="expense-categories"),
    path("categories/<int:pk>/", ExpenseCategoryViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="expense-category-detail"),
    path("", ExpenseViewSet.as_view({"get": "list", "post": "create"}), name="expenses"),
    path("<int:pk>/", ExpenseViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="expense-detail"),
    path("<int:pk>/post/", ExpenseViewSet.as_view({"post": "post_expense"}), name="expense-post"),
]
