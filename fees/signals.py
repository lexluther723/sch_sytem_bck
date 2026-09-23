from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.cache import bust_cache_prefix

from .models import FeePayment, StudentFee


@receiver(post_save, sender=FeePayment)
def update_student_fee(sender, instance, created, **kwargs):
    """
    Automatically update the student's fee account whenever
    a successful payment is recorded.
    """

    if not created:
        return

    # Only successful payments should affect the balance
    if instance.payment_status != FeePayment.PaymentStatus.SUCCESS:
        return

    student_fee = instance.student_fee

    # BEFORE: `sum(payment.amount for payment in student_fee.payments...)`
    # loaded every successful payment ROW for this student's fee
    # account into Python just to add up one column — for a student
    # with a long payment history (many small installments), that's
    # every payment ever made, every single time a new payment comes in.
    #
    # AFTER: `.aggregate(Sum(...))` pushes the addition down to the
    # database, which returns a single number — no payment rows are
    # loaded into Python at all.
    total_paid = student_fee.payments.filter(
        payment_status=FeePayment.PaymentStatus.SUCCESS,
    ).aggregate(total=Sum("amount"))["total"] or 0

    student_fee.amount_paid = total_paid
    student_fee.balance = student_fee.total_fee - total_paid
    student_fee.save(update_fields=["amount_paid", "balance"])

    # A payment changes fee totals shown on the dashboard/reports —
    # bust the cached aggregates so the next view of those pages
    # recomputes fresh numbers instead of serving a stale cached
    # total for up to CACHE_TTL_DASHBOARD_SUMMARY seconds.
    bust_cache_prefix("dashboard")
    bust_cache_prefix("reports")