from rest_framework import serializers

from .models import (
    FeeStructure,
    StudentFee,
    FeePayment,
    MpesaCallbackLog,
)


# =====================================================
# FEE STRUCTURE
# =====================================================

class FeeStructureSerializer(serializers.ModelSerializer):

    total_fee = serializers.ReadOnlyField()

    class Meta:
        model = FeeStructure
        fields = "__all__"


# =====================================================
# STUDENT FEE
# =====================================================

class StudentFeeSerializer(serializers.ModelSerializer):

    student_name = serializers.SerializerMethodField()

    classroom = serializers.SerializerMethodField()

    term = serializers.CharField(
        source="fee_structure.term",
        read_only=True,
    )

    academic_year = serializers.IntegerField(
        source="fee_structure.academic_year",
        read_only=True,
    )

    class Meta:
        model = StudentFee

        fields = [
            "id",
            "student",
            "student_name",
            "classroom",
            "fee_structure",
            "academic_year",
            "term",
            "total_fee",
            "amount_paid",
            "balance",
        ]

        read_only_fields = [
            "amount_paid",
            "balance",
        ]

    def get_student_name(self, obj):
        return (
            f"{obj.student.first_name} "
            f"{obj.student.last_name}"
        )

    def get_classroom(self, obj):
        return str(obj.fee_structure.classroom)


# =====================================================
# FEE PAYMENT
# =====================================================

class FeePaymentSerializer(serializers.ModelSerializer):

    student_name = serializers.SerializerMethodField()

    # React payment form sends transaction_ref.
    # Model field is external_reference.
    transaction_ref = serializers.CharField(
        source="external_reference",
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = FeePayment

        fields = "__all__"

        read_only_fields = [
            "payment_status",
            "mpesa_receipt",
            "merchant_request_id",
            "checkout_request_id",
            "transaction_date",
            "result_code",
            "result_description",
            "is_reconciled",
            "created_at",
            "updated_at",
            "received_by",
        ]

    def get_student_name(self, obj):
        return (
            f"{obj.student_fee.student.first_name} "
            f"{obj.student_fee.student.last_name}"
        )

    def validate(self, data):
        """
        Prevent payments from exceeding the student's
        remaining fee balance.

        This applies to manual/cash/bank payments created
        through FeePaymentViewSet.
        """

        student_fee = data.get(
            "student_fee"
        ) or getattr(
            self.instance,
            "student_fee",
            None,
        )

        amount = data.get("amount")

        if amount is None and self.instance is not None:
            amount = self.instance.amount

        if amount is not None and amount <= 0:
            raise serializers.ValidationError(
                {
                    "amount": (
                        "Amount must be greater than zero."
                    )
                }
            )

        if student_fee is not None and amount is not None:

            available_balance = student_fee.balance

            # When editing an existing successful payment,
            # add the old amount back before validating.
            if (
                self.instance is not None
                and self.instance.student_fee_id == student_fee.id
                and self.instance.payment_status
                == FeePayment.PaymentStatus.SUCCESS
            ):
                available_balance += self.instance.amount

            if amount > available_balance:
                raise serializers.ValidationError(
                    {
                        "amount": (
                            "Amount exceeds remaining "
                            f"balance ({available_balance})."
                        )
                    }
                )

        return data


# =====================================================
# M-PESA CALLBACK LOG
# =====================================================

class MpesaCallbackLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = MpesaCallbackLog
        fields = "__all__"


# =====================================================
# STK PUSH SERIALIZER
# =====================================================

class StkPushSerializer(serializers.Serializer):

    student_fee = serializers.PrimaryKeyRelatedField(
        queryset=StudentFee.objects.all()
    )

    phone_number = serializers.CharField(
        max_length=15
    )

    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    def validate_phone_number(self, value):
        """
        Convert Kenyan phone numbers into
        2547XXXXXXXX format.
        """

        value = value.strip()

        if value.startswith("+254"):
            value = value.replace("+", "")

        elif value.startswith("07"):
            value = "254" + value[1:]

        elif value.startswith("7"):
            value = "254" + value

        if not value.startswith("254"):
            raise serializers.ValidationError(
                "Phone number must start with 254."
            )

        if len(value) != 12 or not value.isdigit():
            raise serializers.ValidationError(
                "Invalid phone number."
            )

        return value

    def validate(self, data):

        student_fee = data["student_fee"]
        amount = data["amount"]

        if amount <= 0:
            raise serializers.ValidationError(
                {
                    "amount": (
                        "Amount must be greater than zero."
                    )
                }
            )

        if amount > student_fee.balance:
            raise serializers.ValidationError(
                {
                    "amount": (
                        "Amount exceeds remaining "
                        f"balance ({student_fee.balance})."
                    )
                }
            )

        return data