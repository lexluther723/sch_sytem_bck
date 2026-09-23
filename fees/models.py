from decimal import Decimal

from django.db import models

from accounts.models import AccountantProfile
from students.models import Student
from classes.models import ClassRoom


# =====================================================
# Fee Structure
# =====================================================
class FeeStructure(models.Model):

    class Term(models.TextChoices):
        TERM_1 = "Term 1", "Term 1"
        TERM_2 = "Term 2", "Term 2"
        TERM_3 = "Term 3", "Term 3"

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="fee_structures",
    )

    academic_year = models.PositiveIntegerField()

    term = models.CharField(
        max_length=20,
        choices=Term.choices,
    )

    tuition_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    activity_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    exam_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    other_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        unique_together = (
            "classroom",
            "academic_year",
            "term",
        )

        ordering = [
            "-academic_year",
            "term",
            "classroom",
        ]

    @property
    def total_fee(self):
        return (
            self.tuition_fee
            + self.activity_fee
            + self.exam_fee
            + self.other_fee
        )

    def __str__(self):
        return (
            f"{self.classroom} - "
            f"{self.term} {self.academic_year}"
        )


# =====================================================
# Student Fee Account
# =====================================================
class StudentFee(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="fee_accounts",
    )

    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name="student_fees",
    )

    total_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        unique_together = (
            "student",
            "fee_structure",
        )

        ordering = [
            "student",
        ]

    def save(self, *args, **kwargs):
        self.balance = self.total_fee - self.amount_paid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - Balance: {self.balance}"


# =====================================================
# Fee Payment
# =====================================================
class FeePayment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "Cash", "Cash"
        BANK = "Bank", "Bank"
        MPESA = "M-Pesa", "M-Pesa"

    class PaymentStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        SUCCESS = "Success", "Success"
        FAILED = "Failed", "Failed"
        CANCELLED = "Cancelled", "Cancelled"

    student_fee = models.ForeignKey(
        StudentFee,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.SUCCESS,
        # Indexed: nearly every fee/dashboard aggregate filters
        # payments by status=Success before summing.
        db_index=True,
    )

    receipt_number = models.CharField(
        max_length=50,
        unique=True,
    )

    payment_date = models.DateField(
        auto_now_add=True,
        # Indexed: monthly/termly fee-collection reports filter and
        # group by this date range on every request.
        db_index=True,
    )

    received_by = models.ForeignKey(
        AccountantProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_payments",
    )

    # =================================================
    # DARAJA / M-PESA FIELDS
    # =================================================

    phone_number = models.CharField(
        max_length=15,
        blank=True,
    )

    external_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Admission number or school payment reference.",
    )

    notes = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Free-text note entered by the accountant "
            "recording the payment."
        ),
    )

    mpesa_receipt = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
    )

    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
    )

    transaction_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    result_code = models.CharField(
        max_length=10,
        blank=True,
    )

    result_description = models.TextField(
        blank=True,
    )

    is_reconciled = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.receipt_number} - "
            f"{self.student_fee.student}"
        )


# =====================================================
# M-Pesa Callback Log
# =====================================================
class MpesaCallbackLog(models.Model):

    checkout_request_id = models.CharField(
        max_length=100,
        unique=True,
    )

    payload = models.JSONField()

    received_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.checkout_request_id