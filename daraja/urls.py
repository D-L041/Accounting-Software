from django.urls import path
from .views import C2BReconcileView, StkPushView, c2b_confirmation, c2b_validation, stk_callback

urlpatterns = [
    path("schools/<int:school_pk>/stk-push/", StkPushView.as_view(), name="daraja-stk-push"),
    path("callbacks/stk/", stk_callback, name="daraja-stk-callback"),
    path("callbacks/c2b/validation/", c2b_validation, name="daraja-c2b-validation"),
    path("callbacks/c2b/confirmation/", c2b_confirmation, name="daraja-c2b-confirmation"),
    path("schools/<int:school_pk>/c2b/", C2BReconcileView.as_view(), name="daraja-c2b-review-queue"),
    path("schools/<int:school_pk>/c2b/<int:notification_pk>/reconcile/", C2BReconcileView.as_view(), name="daraja-c2b-reconcile"),
]
