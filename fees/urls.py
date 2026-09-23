from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DarajaTokenAPIView,
    MpesaCallbackAPIView,
    ReceiptByNumberAPIView,
    StkPushAPIView,
    FeeStructureViewSet,
    StudentFeeViewSet,
    FeePaymentViewSet,
    AccountantDashboardAPIView,
    StudentFeeDashboardAPIView,
)


router = DefaultRouter()


# =====================================================
# FEE STRUCTURES
# =====================================================

router.register(
    r"fee-structures",
    FeeStructureViewSet,
    basename="fee-structure",
)


# =====================================================
# STUDENT FEES
# =====================================================

router.register(
    r"student-fees",
    StudentFeeViewSet,
    basename="student-fee",
)


# =====================================================
# PAYMENTS
# =====================================================

router.register(
    r"payments",
    FeePaymentViewSet,
    basename="fee-payment",
)


# =====================================================
# URLS
# =====================================================

urlpatterns = [

    # -------------------------------------------------
    # DARAJA TOKEN
    # -------------------------------------------------

    path(
        "daraja/token/",
        DarajaTokenAPIView.as_view(),
        name="daraja-token",
    ),

    # -------------------------------------------------
    # STK PUSH
    # -------------------------------------------------

    path(
        "payments/stk-push/",
        StkPushAPIView.as_view(),
        name="stk-push",
    ),

    # -------------------------------------------------
    # ACCOUNTANT DASHBOARD
    # -------------------------------------------------

    path(
        "dashboard/",
        AccountantDashboardAPIView.as_view(),
        name="accountant-dashboard",
    ),

    # -------------------------------------------------
    # INDIVIDUAL STUDENT FEE DASHBOARD
    # -------------------------------------------------

    path(
        "student/<int:student_id>/",
        StudentFeeDashboardAPIView.as_view(),
        name="student-fee-dashboard",
    ),

    # -------------------------------------------------
    # MPESA CALLBACK
    # -------------------------------------------------

    path(
        "mpesa/callback/",
        MpesaCallbackAPIView.as_view(),
        name="mpesa-callback",
    ),

    # -------------------------------------------------
    # ROUTER URLS
    # -------------------------------------------------

    path(
        "",
        include(router.urls),
    ),
    path("receipt/<str:receipt_number>/", ReceiptByNumberAPIView.as_view(), name="receipt-by-number"),
]