from django.db.models import Sum
from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import DarajaService
from students.models import Student

from core.pagination import StandardResultsSetPagination
from core.throttling import SensitiveActionThrottle, duplicate_request_guard
from core.cache import bust_cache_prefix

from .models import (
    FeeStructure,
    StudentFee,
    FeePayment,
    MpesaCallbackLog,
)

from .serializers import (
    FeeStructureSerializer,
    StudentFeeSerializer,
    FeePaymentSerializer,
)

from .permissions import (
    IsSuperAdminOrAccountant,
)


# =====================================================
# FEE STRUCTURE
# =====================================================

class FeeStructureViewSet(viewsets.ModelViewSet):

    queryset = FeeStructure.objects.all().order_by(
        "-academic_year",
        "term",
    )

    serializer_class = FeeStructureSerializer

    permission_classes = [
        IsAuthenticated,
        IsSuperAdminOrAccountant,
    ]

    @action(detail=True, methods=["post"])
    def generate_accounts(self, request, pk=None):

        fee_structure = self.get_object()

        # BEFORE: looped over every student in the classroom and
        # called `get_or_create()` per student — that's up to 2
        # queries (a SELECT then, if missing, an INSERT) PER
        # STUDENT, sequentially, for what is fundamentally a single
        # bulk-insert operation.
        #
        # AFTER: one query to find which students already have an
        # account for this fee structure, then a single bulk
        # `.bulk_create()` for everyone who doesn't. For a 40-student
        # classroom this turns ~80 queries into 2.
        student_ids = list(
            Student.objects.filter(
                classroom=fee_structure.classroom
            ).values_list("id", flat=True)
        )

        existing_student_ids = set(
            StudentFee.objects.filter(
                fee_structure=fee_structure,
                student_id__in=student_ids,
            ).values_list("student_id", flat=True)
        )

        missing_student_ids = [
            sid for sid in student_ids if sid not in existing_student_ids
        ]

        StudentFee.objects.bulk_create(
            [
                StudentFee(
                    student_id=sid,
                    fee_structure=fee_structure,
                    total_fee=fee_structure.total_fee,
                    amount_paid=0,
                    balance=fee_structure.total_fee,
                )
                for sid in missing_student_ids
            ]
        )

        return Response(
            {
                "message": "Fee accounts generated successfully.",
                "created": len(missing_student_ids),
                "skipped": len(existing_student_ids),
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# STUDENT FEE ACCOUNTS
# =====================================================

class StudentFeeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Fee accounts.

    SUPER_ADMIN / ACCOUNTANT / ACADEMIC_COORDINATOR:
        Can view all fee records.

    PARENT:
        Can only view fee records belonging to their children.
    """

    serializer_class = StudentFeeSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        user = self.request.user

        # -------------------------------------------------
        # STAFF
        # -------------------------------------------------

        if getattr(user, "role", None) in [
            "SUPER_ADMIN",
            "ACCOUNTANT",
            "ACADEMIC_COORDINATOR",
        ]:

            return (
                StudentFee.objects
                .select_related(
                    "student",
                    "fee_structure",
                    "fee_structure__classroom",
                )
                .order_by(
                    "student__first_name",
                )
            )

        # -------------------------------------------------
        # PARENT
        # -------------------------------------------------

        if getattr(user, "role", None) == "PARENT":

            parent_profile = getattr(
                user,
                "parent_profile",
                None,
            )

            if not parent_profile:
                return StudentFee.objects.none()

            return (
                StudentFee.objects
                .filter(
                    student__parent=parent_profile
                )
                .select_related(
                    "student",
                    "fee_structure",
                    "fee_structure__classroom",
                )
                .order_by(
                    "student__first_name",
                )
            )

        # -------------------------------------------------
        # OTHER USERS
        # -------------------------------------------------

        return StudentFee.objects.none()


# =====================================================
# STUDENT FEE DASHBOARD
# =====================================================

class StudentFeeDashboardAPIView(APIView):
    """
    Return complete fee information for one student.

    SUPER_ADMIN / ACCOUNTANT / ACADEMIC_COORDINATOR:
        Can view any student.

    PARENT:
        Can only view their own child.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, student_id):

        user = request.user

        # -------------------------------------------------
        # GET STUDENT
        # -------------------------------------------------

        try:

            student = (
                Student.objects
                .select_related(
                    "parent",
                    "classroom",
                )
                .get(
                    id=student_id
                )
            )

        except Student.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Student not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -------------------------------------------------
        # AUTHORIZE USER
        # -------------------------------------------------

        role = getattr(
            user,
            "role",
            None,
        )

        allowed_staff_roles = [
            "SUPER_ADMIN",
            "ACCOUNTANT",
            "ACADEMIC_COORDINATOR",
        ]

        # -------------------------------------------------
        # PARENT
        # -------------------------------------------------

        if role == "PARENT":

            parent_profile = getattr(
                user,
                "parent_profile",
                None,
            )

            if not parent_profile:

                return Response(
                    {
                        "success": False,
                        "message": "Parent profile not found.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if student.parent_id != parent_profile.id:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "You are not authorized to view "
                            "this student's fees."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # -------------------------------------------------
        # STAFF
        # -------------------------------------------------

        elif role not in allowed_staff_roles:

            return Response(
                {
                    "success": False,
                    "message": (
                        "You are not authorized to view "
                        "this student's fees."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -------------------------------------------------
        # GET FEE ACCOUNTS
        # -------------------------------------------------

        fee_accounts = (
            StudentFee.objects
            .filter(
                student=student
            )
            .select_related(
                "student",
                "fee_structure",
                "fee_structure__classroom",
            )
            .order_by(
                "-fee_structure__academic_year",
                "-fee_structure__term",
            )
        )

        # -------------------------------------------------
        # SERIALIZE
        # -------------------------------------------------

        serializer = StudentFeeSerializer(
            fee_accounts,
            many=True,
        )

        # -------------------------------------------------
        # CALCULATE SUMMARY
        # -------------------------------------------------

        total_fee = sum(
            float(fee.total_fee)
            for fee in fee_accounts
        )

        total_paid = sum(
            float(fee.amount_paid)
            for fee in fee_accounts
        )

        total_balance = sum(
            float(fee.balance)
            for fee in fee_accounts
        )

        # -------------------------------------------------
        # STUDENT CLASSROOM
        # -------------------------------------------------

        classroom_name = None

        if student.classroom:
            classroom_name = (
                getattr(
                    student.classroom,
                    "name",
                    None,
                )
                or getattr(
                    student.classroom,
                    "class_name",
                    None,
                )
                or str(student.classroom)
            )

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return Response(
            {
                "success": True,

                "student": {
                    "id": student.id,

                    "admission_number": (
                        student.admission_number
                    ),

                    "first_name": (
                        student.first_name
                    ),

                    "last_name": (
                        student.last_name
                    ),

                    "classroom": classroom_name,
                },

                "summary": {
                    "total_fee": total_fee,
                    "total_paid": total_paid,
                    "total_balance": total_balance,
                },

                "fee_accounts": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# FEE PAYMENTS
# =====================================================

class FeePaymentViewSet(viewsets.ModelViewSet):

    queryset = (
        FeePayment.objects
        .select_related(
            "student_fee",
            "student_fee__student",
            "received_by",
        )
        .order_by(
            "-payment_date",
        )
    )

    serializer_class = FeePaymentSerializer

    permission_classes = [
        IsAuthenticated,
        IsSuperAdminOrAccountant,
    ]

    def perform_create(self, serializer):
        """
        received_by is controlled by the backend.

        The client cannot spoof another accountant.
        """

        accountant_profile = getattr(
            self.request.user,
            "accountant_profile",
            None,
        )

        serializer.save(
            received_by=accountant_profile
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def successful(self, request):

        queryset = self.get_queryset().filter(
            payment_status=FeePayment.PaymentStatus.SUCCESS
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def pending(self, request):

        queryset = self.get_queryset().filter(
            payment_status=FeePayment.PaymentStatus.PENDING
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data
        )


# =====================================================
# ACCOUNTANT DASHBOARD
# =====================================================

class AccountantDashboardAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsSuperAdminOrAccountant,
    ]

    def get(self, request):

        total_expected = (
            StudentFee.objects.aggregate(
                total=Sum("total_fee")
            )["total"]
            or 0
        )

        total_paid = (
            StudentFee.objects.aggregate(
                total=Sum("amount_paid")
            )["total"]
            or 0
        )

        total_balance = (
            StudentFee.objects.aggregate(
                total=Sum("balance")
            )["total"]
            or 0
        )

        total_payments = (
            FeePayment.objects.count()
        )

        return Response(
            {
                "students": StudentFee.objects.count(),
                "payments": total_payments,
                "total_expected": total_expected,
                "total_paid": total_paid,
                "total_balance": total_balance,
            }
        )


# =====================================================
# TEST DARAJA CONNECTION
# =====================================================

class DarajaTokenAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsSuperAdminOrAccountant,
    ]

    def get(self, request):

        try:

            token = (
                DarajaService
                .get_access_token()
            )

            return Response(
                {
                    "success": True,
                    "access_token": token,
                }
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# =====================================================
# STK PUSH
# =====================================================

class StkPushAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    # ---------------------------------------------------------
    # PREVENT DUPLICATE / RUNAWAY STK PUSHES
    #
    # BEFORE: nothing stopped a double-tap on "Pay Now", a slow
    # network causing the frontend to retry, or a parent refreshing
    # mid-request from firing a SECOND STK push to the same phone
    # for the same student while the first one is still pending —
    # each one is a real request to Safaricom's Daraja API (an
    # external network call with real cost/rate limits on THEIR
    # side too) and a real prompt on the parent's phone.
    #
    # AFTER:
    #  - `throttle_classes`/`throttle_scope`: caps how often this
    #    user can call this endpoint at all (rate limiting).
    #  - `duplicate_request_guard`: a short-lived (20s) lock keyed on
    #    (user, student, amount) so an identical repeat request
    #    within that window is rejected instantly with 409, before
    #    it ever reaches Daraja — this is idempotency protection,
    #    which a rate limit alone does NOT provide.
    # ---------------------------------------------------------
    throttle_classes = [SensitiveActionThrottle]
    throttle_scope = "mpesa_stk_push"

    @duplicate_request_guard(
        lambda request, *a, **kw: (
            f"stk-push:{request.user.id}:"
            f"{request.data.get('student_id')}:"
            f"{request.data.get('amount')}"
        ),
        timeout=20,
    )
    def post(self, request):

        # -------------------------------------------------
        # GET REQUEST DATA
        # -------------------------------------------------

        student_id = request.data.get(
            "student_id"
        )

        amount = request.data.get(
            "amount"
        )

        phone_number = request.data.get(
            "phone"
        )

        description = (
            request.data.get("description")
            or "School Fees"
        )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not student_id:

            return Response(
                {
                    "success": False,
                    "message": "student_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not amount:

            return Response(
                {
                    "success": False,
                    "message": "amount is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not phone_number:

            return Response(
                {
                    "success": False,
                    "message": "phone is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # GET STUDENT
        # -------------------------------------------------

        try:

            student = (
                Student.objects
                .select_related(
                    "parent",
                    "classroom",
                )
                .get(
                    id=student_id
                )
            )

        except Student.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Student not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -------------------------------------------------
        # AUTHORIZE USER
        # -------------------------------------------------

        user = request.user

        is_parent = (
            getattr(
                user,
                "role",
                None,
            )
            == "PARENT"
        )

        if is_parent:

            parent_profile = getattr(
                user,
                "parent_profile",
                None,
            )

            if (
                not parent_profile
                or student.parent_id
                != parent_profile.id
            ):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "You are not authorized "
                            "to pay fees for this student."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        else:

            allowed_roles = [
                "SUPER_ADMIN",
                "ACCOUNTANT",
                "ACADEMIC_COORDINATOR",
            ]

            if (
                getattr(
                    user,
                    "role",
                    None,
                )
                not in allowed_roles
            ):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "You are not authorized "
                            "to make this payment."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # -------------------------------------------------
        # GET FEE ACCOUNT
        # -------------------------------------------------

        student_fee = (
            StudentFee.objects
            .select_related(
                "student",
                "fee_structure",
            )
            .filter(
                student=student
            )
            .order_by(
                "-fee_structure__academic_year",
                "-fee_structure__term",
            )
            .first()
        )

        if not student_fee:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No fee account exists "
                        "for this student."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # VALIDATE AMOUNT
        # -------------------------------------------------

        try:

            amount = int(
                float(amount)
            )

        except (
            ValueError,
            TypeError,
        ):

            return Response(
                {
                    "success": False,
                    "message": "Invalid payment amount.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount < 100:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Payment amount must be "
                        "at least KES 100."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # CHECK BALANCE
        # -------------------------------------------------

        if amount > float(
            student_fee.balance
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "Payment amount cannot "
                        "exceed the student's "
                        f"fee balance of "
                        f"KES {student_fee.balance}."
                    ),
                    "balance": student_fee.balance,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # NORMALIZE PHONE
        # -------------------------------------------------

        phone_number = (
            str(phone_number)
            .replace(" ", "")
            .replace("-", "")
            .replace("+", "")
        )

        if phone_number.startswith("0"):

            phone_number = (
                "254"
                + phone_number[1:]
            )

        elif phone_number.startswith("7"):

            phone_number = (
                "254"
                + phone_number
            )

        if not phone_number.startswith("2547"):

            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid Kenyan "
                        "M-Pesa phone number."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # RECEIVED BY
        # -------------------------------------------------

        accountant = getattr(
            user,
            "accountant_profile",
            None,
        )

        # -------------------------------------------------
        # CREATE PAYMENT
        # -------------------------------------------------

        payment = FeePayment.objects.create(

            student_fee=student_fee,

            amount=amount,

            payment_method=(
                FeePayment.PaymentMethod.MPESA
            ),

            payment_status=(
                FeePayment.PaymentStatus.PENDING
            ),

            receipt_number=(
                "PENDING-"
                f"{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
            ),

            phone_number=phone_number,

            received_by=accountant,
        )

        # -------------------------------------------------
        # SEND STK PUSH
        # -------------------------------------------------

        try:

            response = (
                DarajaService.stk_push(
                    phone_number=phone_number,
                    amount=amount,
                    account_reference=(
                        str(
                            student.admission_number
                        )
                    ),
                    transaction_desc=(
                        description[:100]
                        if description
                        else (
                            f"School Fees - "
                            f"{student.first_name} "
                            f"{student.last_name}"
                        )
                    ),
                )
            )

        except Exception as e:

            payment.payment_status = (
                FeePayment.PaymentStatus.FAILED
            )

            payment.result_description = (
                str(e)
            )

            payment.save(
                update_fields=[
                    "payment_status",
                    "result_description",
                ]
            )

            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # SAVE DARAJA IDS
        # -------------------------------------------------

        payment.merchant_request_id = (
            response.get(
                "MerchantRequestID",
                "",
            )
        )

        payment.checkout_request_id = (
            response.get(
                "CheckoutRequestID",
                "",
            )
        )

        payment.save(
            update_fields=[
                "merchant_request_id",
                "checkout_request_id",
            ]
        )

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return Response(
            {
                "success": True,

                "message": (
                    "STK Push sent successfully."
                ),

                "payment_id": payment.id,

                "student_id": student.id,

                "student_name": (
                    f"{student.first_name} "
                    f"{student.last_name}"
                ),

                "amount": payment.amount,

                "merchant_request_id": (
                    payment.merchant_request_id
                ),

                "checkout_request_id": (
                    payment.checkout_request_id
                ),

                "customer_message": (
                    response.get(
                        "CustomerMessage"
                    )
                ),
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# MPESA CALLBACK
# =====================================================

class MpesaCallbackAPIView(APIView):

    permission_classes = [
        AllowAny
    ]

    def post(self, request):

        data = request.data

        callback = (
            data
            .get("Body", {})
            .get("stkCallback", {})
        )

        checkout_request_id = (
            callback.get(
                "CheckoutRequestID"
            )
        )

        if not checkout_request_id:

            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "No CheckoutRequestID.",
                }
            )

        # -------------------------------------------------
        # SAVE CALLBACK
        # -------------------------------------------------

        MpesaCallbackLog.objects.get_or_create(
            checkout_request_id=checkout_request_id,
            defaults={
                "payload": data,
            },
        )

        # -------------------------------------------------
        # FIND PAYMENT
        # -------------------------------------------------

        try:

            payment = (
                FeePayment.objects.get(
                    checkout_request_id=checkout_request_id
                )
            )

        except FeePayment.DoesNotExist:

            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Payment not found.",
                }
            )

        # -------------------------------------------------
        # PREVENT DUPLICATE PROCESSING
        # -------------------------------------------------

        if (
            payment.payment_status
            == FeePayment.PaymentStatus.SUCCESS
        ):

            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Already processed.",
                }
            )

        result_code = callback.get(
            "ResultCode"
        )

        result_desc = callback.get(
            "ResultDesc"
        )

        payment.result_code = str(
            result_code
        )

        payment.result_description = (
            result_desc
        )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if result_code == 0:

            metadata = {}

            items = (
                callback
                .get(
                    "CallbackMetadata",
                    {},
                )
                .get(
                    "Item",
                    [],
                )
            )

            for item in items:

                name = item.get(
                    "Name"
                )

                if name:

                    metadata[name] = (
                        item.get("Value")
                    )

            # -------------------------------------------------
            # MPESA RECEIPT
            # -------------------------------------------------

            payment.mpesa_receipt = (
                metadata.get(
                    "MpesaReceiptNumber"
                )
            )

            # -------------------------------------------------
            # PHONE
            # -------------------------------------------------

            if metadata.get(
                "PhoneNumber"
            ):

                payment.phone_number = (
                    str(
                        metadata.get(
                            "PhoneNumber"
                        )
                    )
                )

            # -------------------------------------------------
            # TRANSACTION DATE
            # -------------------------------------------------

            payment.transaction_date = (
                timezone.now()
            )

            # -------------------------------------------------
            # UPDATE FEE ACCOUNT
            # -------------------------------------------------

            with transaction.atomic():

                student_fee = (
                    StudentFee.objects
                    .select_for_update()
                    .get(
                        id=payment.student_fee_id
                    )
                )

                student_fee.amount_paid = (
                    student_fee.amount_paid
                    + payment.amount
                )

                student_fee.balance = max(
                    student_fee.total_fee
                    - student_fee.amount_paid,
                    0,
                )

                student_fee.save(
                    update_fields=[
                        "amount_paid",
                        "balance",
                    ]
                )

                payment.payment_status = (
                    FeePayment.PaymentStatus.SUCCESS
                )

                payment.save()

        # -------------------------------------------------
        # FAILED / CANCELLED
        # -------------------------------------------------

        else:

            payment.payment_status = (
                FeePayment.PaymentStatus.FAILED
            )

            payment.save(
                update_fields=[
                    "result_code",
                    "result_description",
                    "payment_status",
                ]
            )

        # -------------------------------------------------
        # ACKNOWLEDGE SAFARICOM
        # -------------------------------------------------

        return Response(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted",
            }
        )


# =====================================================
# GET RECEIPT BY RECEIPT NUMBER
# =====================================================

class ReceiptByNumberAPIView(APIView):
    """
    Return payment/receipt details using receipt_number.

    Staff can view any receipt.

    Parents can only view receipts belonging to
    their own children.
    """

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request, receipt_number):

        try:

            payment = (
                FeePayment.objects
                .select_related(
                    "student_fee",
                    "student_fee__student",
                    "student_fee__student__parent",
                )
                .get(
                    receipt_number=receipt_number
                )
            )

        except FeePayment.DoesNotExist:

            return Response(
                {
                    "detail": "Receipt not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -------------------------------------------------
        # AUTHORIZE RECEIPT ACCESS
        # -------------------------------------------------

        user = request.user
        role = getattr(
            user,
            "role",
            None,
        )

        allowed_staff_roles = [
            "SUPER_ADMIN",
            "ACCOUNTANT",
            "ACADEMIC_COORDINATOR",
        ]

        if role == "PARENT":

            parent_profile = getattr(
                user,
                "parent_profile",
                None,
            )

            if (
                not parent_profile
                or payment.student_fee.student.parent_id
                != parent_profile.id
            ):

                return Response(
                    {
                        "detail": (
                            "You are not authorized "
                            "to view this receipt."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        elif role not in allowed_staff_roles:

            return Response(
                {
                    "detail": (
                        "You are not authorized "
                        "to view this receipt."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -------------------------------------------------
        # RECEIPT DATA
        # -------------------------------------------------

        student = payment.student_fee.student

        data = {
            "id": payment.id,

            "receipt_number": (
                payment.receipt_number
            ),

            "student_name": (
                f"{student.first_name} "
                f"{student.last_name}"
            ),

            "admission_number": (
                student.admission_number
            ),

            "amount": payment.amount,

            "payment_method": (
                payment.payment_method
            ),

            "payment_status": (
                payment.payment_status
            ),

            "payment_date": (
                payment.payment_date
            ),

            "phone_number": (
                payment.phone_number
            ),

            "mpesa_receipt": (
                payment.mpesa_receipt
            ),

            "result_description": (
                payment.result_description
            ),

            "transaction_date": (
                payment.transaction_date
            ),
        }

        return Response(
            data,
            status=status.HTTP_200_OK,
        )