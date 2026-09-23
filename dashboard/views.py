from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Max, Min, Q
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.cache import get_or_set_cached_indexed
from core.pagination import StandardResultsSetPagination, paginate_queryset_response

from timetable.models import Timetable
from anouncements.models import Announcement

from dashboard.permissions import (
    IsAcademicCoordinator,
    IsDashboardUser,
    IsTeacher,
)

from results.models import (
    Result,
    StudentResult,
    StudentTermResult,
    ResultSubmission,
    Assessment,
)

from students.models import Student

from assignments.models import (
    TeacherProfile,
    TeacherAssignment,
)

from accounts.models import ParentProfile
from classes.models import ClassRoom
from subjects.models import Subject
from attendance.models import Attendance
from fees.models import FeePayment, StudentFee
from exams.models import Exam
from notifiations.models import Notification

from .serializers import (
    AttendanceSummarySerializer,
    DashboardFeeSummarySerializer,
    DashboardSerializer,
    ExamPerformanceSerializer,
    RecentPaymentSerializer,
    TopStudentSerializer,
    UpcomingNotificationSerializer,
    TopClassSerializer,
    RecentAdmissionSerializer,
    ParentDashboardSerializer,
    ParentChildSerializer,
    ParentChildDetailsSerializer,
    TeacherStudentSerializer,
    TeacherStudentDetailsSerializer,
    TeacherStudentResultUpdateSerializer,
    TeacherDashboardSerializer,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_class_teacher(user):
    if not hasattr(user, "teacher_profile"):
        return False

    return ClassRoom.objects.filter(
        class_teacher=user.teacher_profile
    ).exists()


def calculate_grade(marks):
    """
    Calculate CBC grade from marks.
    """

    if marks is None:
        return "N/A"

    marks = float(marks)

    if marks >= 90:
        return "EE1"
    elif marks >= 75:
        return "EE2"
    elif marks >= 58:
        return "ME1"
    elif marks >= 41:
        return "ME2"
    elif marks >= 31:
        return "AE1"
    elif marks >= 21:
        return "AE2"
    elif marks >= 11:
        return "BE1"
    elif marks >= 1:
        return "BE2"

    return "N/A"


def calculate_student_subject_result(student, assessment):
    """
    Calculate a student's result for an assessment.
    """

    # FIXED: Result has no `assessment` field - it reaches the
    # assessment through submission -> ResultSubmission.assessment.
    result = Result.objects.filter(
        student=student,
        submission__assessment=assessment,
    ).select_related("grade", "submission__assessment").first()

    if not result:
        return None

    return result


def calculate_student_term_result(
    student,
    classroom,
    term,
    academic_year,
):
    """
    Calculate the student's average for a term.

    This is intentionally kept independent of fields that may
    differ between Result/Assessment implementations.
    """

    results = Result.objects.filter(
        student=student,
    )

    # Filter assessment-related fields only if they exist.
    assessment_fields = {
        field.name
        for field in Assessment._meta.get_fields()
    }

    if "classroom" in assessment_fields:
        results = results.filter(
            assessment__classroom=classroom
        )

    if "term" in assessment_fields:
        results = results.filter(
            assessment__term=term
        )

    if "academic_year" in assessment_fields:
        results = results.filter(
            assessment__academic_year=academic_year
        )

    average = results.aggregate(
        average=Avg("marks")
    )["average"]

    if average is None:
        return None

    return {
        "student": student,
        "classroom": classroom,
        "term": term,
        "academic_year": academic_year,
        "average": round(float(average), 2),
        "grade": calculate_grade(average),
    }


def calculate_class_positions(
    classroom,
    term,
    academic_year,
):
    """
    Calculate class positions based on term averages.
    """

    students = Student.objects.filter(
        classroom=classroom
    )

    results = []

    for student in students:
        result = calculate_student_term_result(
            student=student,
            classroom=classroom,
            term=term,
            academic_year=academic_year,
        )

        if result:
            results.append(result)

    results.sort(
        key=lambda item: item["average"],
        reverse=True,
    )

    for position, result in enumerate(
        results,
        start=1,
    ):
        result["position"] = position

    return results


# ============================================================
# TOP OUTSTANDING STUDENTS
# ============================================================

class TopOutstandingStudentsAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        # This query is already following best practice — `.values()`
        # + `.annotate(Avg(...))` computes the ranking entirely in
        # the database and returns plain dicts instead of full model
        # instances, so there's no extra optimization to make to the
        # QUERY itself. What was missing is that this ranking is
        # recomputed from scratch (a GROUP BY average across every
        # Result row) on every single dashboard view — caching it
        # avoids repeating that scan on every page load.
        data = get_or_set_cached_indexed(
            "dashboard:top_outstanding_students",
            parts=("global",),
            builder=self._build_top_students,
            timeout=settings.CACHE_TTL_DASHBOARD_SUMMARY,
        )

        serializer = TopStudentSerializer(data, many=True)
        return Response(serializer.data)

    @staticmethod
    def _build_top_students():
        students = (
            Result.objects
            .values(
                "student",
                "student__photo",
                "student__assessment_number",
                "student__admission_number",
                "student__first_name",
                "student__last_name",
                "student__classroom__grade",
            )
            .annotate(
                average_score=Avg("marks")
            )
            .exclude(
                average_score=None
            )
            .order_by(
                "-average_score"
            )[:10]
        )

        data = []

        for position, student in enumerate(
            students,
            start=1,
        ):
            average = round(
                float(student["average_score"]),
                2,
            )

            data.append({
                "position": position,
                "photo": student["student__photo"],
                "assessment_number": student[
                    "student__assessment_number"
                ],
                "admission_number": student[
                    "student__admission_number"
                ],
                "student_name": (
                    f'{student["student__first_name"]} '
                    f'{student["student__last_name"]}'
                ),
                "classroom": student[
                    "student__classroom__grade"
                ],
                "average_score": average,
                "grade": calculate_grade(average),
            })

        return data


# ============================================================
# MAIN DASHBOARD
# ============================================================

class DashboardAPIView(APIView):

    permission_classes = [IsAcademicCoordinator]

    def get(self, request):

        # BEFORE: every dashboard page load ran ~13 separate COUNT /
        # aggregate queries against the database — for a summary
        # screen that's opened repeatedly (every login, every
        # refresh, often by several staff members at once) but only
        # actually CHANGES when a student/payment/attendance record
        # is added — i.e. rarely, relative to how often it's viewed.
        #
        # AFTER, two changes:
        #  1. Related counts are merged into single `.aggregate()`
        #     calls using conditional `Count(..., filter=Q(...))`
        #     expressions, so "total/active/boys/girls" is 1 query
        #     instead of 4, and "total/present attendance" is 1
        #     query instead of 2.
        #  2. The whole computed dict is cached for
        #     `CACHE_TTL_DASHBOARD_SUMMARY` seconds (see core/cache.py
        #     + settings.py) using a cache-aside pattern — the
        #     expensive aggregation only runs on a cache miss, and is
        #     proactively invalidated the moment a payment is
        #     recorded (fees/signals.py) rather than waiting out a
        #     stale window.
        data = get_or_set_cached_indexed(
            "dashboard:summary",
            parts=("global",),
            builder=self._build_summary,
            timeout=settings.CACHE_TTL_DASHBOARD_SUMMARY,
        )

        serializer = DashboardSerializer(data)
        return Response(serializer.data)

    @staticmethod
    def _build_summary():
        student_counts = Student.objects.aggregate(
            total_students=Count("id"),
            active_students=Count(
                "id", filter=Q(status=Student.Status.ACTIVE)
            ),
            boys=Count("id", filter=Q(gender=Student.Gender.MALE)),
            girls=Count("id", filter=Q(gender=Student.Gender.FEMALE)),
        )

        total_teachers = TeacherProfile.objects.count()
        total_parents = ParentProfile.objects.count()
        total_classes = ClassRoom.objects.count()
        total_subjects = Subject.objects.count()

        fees = StudentFee.objects.aggregate(
            total_fee=Sum("total_fee"),
            total_paid=Sum("amount_paid"),
            total_balance=Sum("balance"),
        )

        # FIXED: this aggregated over EVERY attendance record ever
        # created and reported the result as "attendance_today". It was
        # both wrong and progressively slower - a full scan of the
        # fastest-growing table in the schema on every cache miss.
        # Now scoped to the current date via the indexed
        # AttendanceSubmission.date column.
        attendance_counts = Attendance.objects.filter(
            submission__date=timezone.localdate(),
        ).aggregate(
            total_attendance=Count("id"),
            present=Count(
                "id", filter=Q(status=Attendance.Status.PRESENT)
            ),
        )

        total_attendance = attendance_counts["total_attendance"]
        present = attendance_counts["present"]

        attendance_today = (
            round((present / total_attendance) * 100, 2)
            if total_attendance > 0
            else Decimal("0.00")
        )

        total_exams = Exam.objects.count()
        total_results = Result.objects.count()

        unread_notifications = Notification.objects.filter(
            is_read=False
        ).count()

        return {
            "total_students": student_counts["total_students"],
            "active_students": student_counts["active_students"],
            "boys": student_counts["boys"],
            "girls": student_counts["girls"],
            "total_teachers": total_teachers,
            "total_classes": total_classes,
            "total_subjects": total_subjects,
            "total_parents": total_parents,
            "attendance_today": attendance_today,
            "total_fee": fees["total_fee"] or Decimal("0.00"),
            "total_paid": fees["total_paid"] or Decimal("0.00"),
            "total_balance": fees["total_balance"] or Decimal("0.00"),
            "total_exams": total_exams,
            "total_results": total_results,
            "unread_notifications": unread_notifications,
        }


# ============================================================
# TOP PERFORMING CLASSES
# ============================================================

class TopPerformingClassesAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        classes = (
            Result.objects
            .values(
                "student__classroom",
                "student__classroom__grade",
            )
            .annotate(
                average_score=Avg("marks"),
                total_students=Count(
                    "student",
                    distinct=True,
                ),
            )
            .order_by(
                "-average_score"
            )
        )

        data = []

        for position, classroom in enumerate(
            classes,
            start=1,
        ):
            data.append({
                "position": position,
                "classroom": classroom[
                    "student__classroom__grade"
                ],
                "average_score": round(
                    float(
                        classroom["average_score"]
                        or 0
                    ),
                    2,
                ),
                "total_students": classroom[
                    "total_students"
                ],
            })

        serializer = TopClassSerializer(
            data,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# RECENT FEE PAYMENTS
# ============================================================

class RecentFeePaymentsAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        payments = (
            FeePayment.objects
            .select_related(
                "student_fee__student"
            )
            .order_by(
                "-payment_date"
            )[:10]
        )

        data = []

        for payment in payments:

            student = payment.student_fee.student

            data.append({
                "receipt_number": payment.receipt_number,
                "student_name": (
                    f"{student.first_name} "
                    f"{student.last_name}"
                ),
                "admission_number": (
                    student.admission_number
                ),
                "amount": payment.amount,
                "payment_method": payment.payment_method,
                "payment_date": payment.payment_date,
                "payment_status": payment.payment_status,
            })

        serializer = RecentPaymentSerializer(
            data,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# RECENT ADMISSIONS
# ============================================================

class RecentAdmissionsAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        students = (
            Student.objects
            .select_related("classroom")
            .order_by(
                "-date_admitted"
            )[:10]
        )

        data = []

        for student in students:

            data.append({
                "photo": student.photo,
                "admission_number": (
                    student.admission_number
                ),
                "assessment_number": (
                    student.assessment_number
                ),
                "student_name": (
                    f"{student.first_name} "
                    f"{student.last_name}"
                ),
                "classroom": (
                    str(student.classroom)
                    if student.classroom
                    else None
                ),
                "date_admitted": (
                    student.date_admitted
                ),
            })

        serializer = RecentAdmissionSerializer(
            data,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# TODAY ATTENDANCE
# ============================================================

class TodayAttendanceSummaryAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        today = timezone.localdate()

        attendance = Attendance.objects.filter(
            marked_at__date=today
        )

        present = attendance.filter(
            status=Attendance.Status.PRESENT
        ).count()

        absent = attendance.filter(
            status=Attendance.Status.ABSENT
        ).count()

        excused = attendance.filter(
            status=Attendance.Status.EXCUSED
        ).count()

        total = attendance.count()

        percentage = (
            round(
                (present / total) * 100,
                2,
            )
            if total > 0
            else 0
        )

        serializer = AttendanceSummarySerializer({
            "present": present,
            "absent": absent,
            "excused": excused,
            "total": total,
            "attendance_percentage": percentage,
        })

        return Response(serializer.data)


# ============================================================
# DASHBOARD FEE SUMMARY
# ============================================================

class DashboardFeeSummaryAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        fees = StudentFee.objects.aggregate(
            expected_fee=Sum("total_fee"),
            collected_fee=Sum("amount_paid"),
            outstanding_fee=Sum("balance"),
        )

        expected = (
            fees["expected_fee"]
            or Decimal("0.00")
        )

        collected = (
            fees["collected_fee"]
            or Decimal("0.00")
        )

        outstanding = (
            fees["outstanding_fee"]
            or Decimal("0.00")
        )

        percentage = (
            round(
                (collected / expected) * 100,
                2,
            )
            if expected > 0
            else Decimal("0.00")
        )

        total_transactions = FeePayment.objects.count()

        serializer = DashboardFeeSummarySerializer({
            "expected_fee": expected,
            "collected_fee": collected,
            "outstanding_fee": outstanding,
            "collection_percentage": percentage,
            "total_transactions": total_transactions,
        })

        return Response(serializer.data)


# ============================================================
# EXAM PERFORMANCE
# ============================================================

class ExamPerformanceDashboardAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        total_exams = Exam.objects.count()

        published_results = Result.objects.count()

        pending_results = max(
            total_exams - published_results,
            0,
        )

        stats = Result.objects.aggregate(
            overall_average=Avg("marks"),
            highest_score=Max("marks"),
            lowest_score=Min("marks"),
        )

        serializer = ExamPerformanceSerializer({
            "total_exams": total_exams,
            "published_results": published_results,
            "pending_results": pending_results,
            "overall_average": (
                stats["overall_average"]
                or Decimal("0.00")
            ),
            "highest_score": (
                stats["highest_score"]
                or Decimal("0.00")
            ),
            "lowest_score": (
                stats["lowest_score"]
                or Decimal("0.00")
            ),
        })

        return Response(serializer.data)


# ============================================================
# UPCOMING NOTIFICATIONS
# ============================================================

class UpcomingNotificationsAPIView(APIView):

    permission_classes = [IsDashboardUser]

    def get(self, request):

        announcements = (
            Announcement.objects
            .select_related("created_by")
            .order_by(
                "-created_at"
            )[:10]
        )

        data = []

        for announcement in announcements:

            data.append({
                "id": announcement.id,
                "title": announcement.title,
                "message": announcement.message,
                "priority": announcement.priority,
                "target": announcement.target,
                "created_at": announcement.created_at,
                "created_by": (
                    announcement.created_by.get_full_name()
                    if announcement.created_by
                    else "System"
                ),
            })

        serializer = UpcomingNotificationSerializer(
            data,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# PARENT DASHBOARD
# ============================================================

class ParentDashboardAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        parent = ParentProfile.objects.filter(
            user=request.user
        ).first()

        if not parent:
            return Response(
                {
                    "detail": (
                        "Parent profile not found."
                    )
                },
                status=404,
            )

        students = Student.objects.filter(
            parent=parent
        )

        children_count = students.count()

        fee_summary = StudentFee.objects.filter(
            student__in=students
        ).aggregate(
            total_balance=Sum("balance")
        )

        total_fee_balance = (
            fee_summary["total_balance"]
            or Decimal("0.00")
        )

        attendance = Attendance.objects.filter(
            student__in=students
        )

        total = attendance.count()

        present = attendance.filter(
            status=Attendance.Status.PRESENT
        ).count()

        overall_attendance = (
            round(
                (present / total) * 100,
                2,
            )
            if total > 0
            else Decimal("0.00")
        )

        unread_notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()

        announcements = (
            Announcement.objects
            .order_by("-created_at")[:5]
        )

        serializer = ParentDashboardSerializer({
            "parent_name": request.user.get_full_name(),
            "children_count": children_count,
            "total_fee_balance": total_fee_balance,
            "overall_attendance": overall_attendance,
            "unread_notifications": unread_notifications,
            "announcements": announcements,
        })

        return Response(serializer.data)


# ============================================================
# PARENT CHILDREN
# ============================================================

class ParentChildrenAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        parent = ParentProfile.objects.filter(
            user=request.user
        ).first()

        if not parent:
            return Response([])

        students = (
            Student.objects
            .filter(parent=parent)
            .select_related(
                "classroom",
                "classroom__class_teacher",
                "classroom__class_teacher__user",
            )
        )

        data = []

        for student in students:

            teacher = (
                student.classroom.class_teacher
                if student.classroom
                else None
            )

            attendance = Attendance.objects.filter(
                student=student
            )

            total = attendance.count()

            present = attendance.filter(
                status=Attendance.Status.PRESENT
            ).count()

            attendance_percentage = (
                round(
                    (present / total) * 100,
                    2,
                )
                if total > 0
                else 0
            )

            fee_balance = (
                StudentFee.objects
                .filter(student=student)
                .aggregate(
                    balance=Sum("balance")
                )["balance"]
                or Decimal("0.00")
            )

            latest_result = (
                StudentTermResult.objects
                .filter(student=student)
                .order_by("-id")
                .first()
            )

            data.append({
                "id": student.id,
                "photo": student.photo,
                "admission_number": (
                    student.admission_number
                ),
                "assessment_number": (
                    student.assessment_number
                ),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "grade": (
                    student.classroom.grade
                    if student.classroom
                    else None
                ),
                "stream": (
                    student.classroom.stream
                    if student.classroom
                    else None
                ),
                "class_teacher": (
                    teacher.user.get_full_name()
                    if teacher
                    else None
                ),
                "teacher_phone": (
                    teacher.user.phone_number
                    if teacher
                    else None
                ),
                "attendance_percentage": (
                    attendance_percentage
                ),
                "latest_grade": (
                    latest_result.overall_grade
                    if latest_result
                    else "-"
                ),
                "fee_balance": fee_balance,
                "status": student.status,
            })

        serializer = ParentChildSerializer(
            data,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# PARENT CHILD DETAILS
# ============================================================

class ParentChildDetailsAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, id):

        parent = get_object_or_404(
            ParentProfile,
            user=request.user,
        )

        student = get_object_or_404(
            Student.objects.select_related(
                "classroom",
                "classroom__class_teacher",
                "classroom__class_teacher__user",
            ),
            id=id,
            parent=parent,
        )

        classroom = student.classroom

        teacher = (
            classroom.class_teacher
            if classroom
            else None
        )

        attendance = Attendance.objects.filter(
            student=student
        )

        total = attendance.count()

        present = attendance.filter(
            status=Attendance.Status.PRESENT
        ).count()

        attendance_percentage = (
            round(
                (present / total) * 100,
                2,
            )
            if total > 0
            else 0
        )

        fee_balance = (
            StudentFee.objects
            .filter(student=student)
            .aggregate(
                balance=Sum("balance")
            )["balance"]
            or Decimal("0.00")
        )

        latest_result = (
            StudentTermResult.objects
            .filter(student=student)
            .order_by("-id")
            .first()
        )

        data = {
            "id": student.id,

            "photo": (
                student.photo.url
                if student.photo
                else None
            ),

            "admission_number": (
                student.admission_number
            ),

            "assessment_number": (
                student.assessment_number
            ),

            "first_name": student.first_name,
            "last_name": student.last_name,
            "gender": student.gender,
            "date_of_birth": student.date_of_birth,

            "grade": (
                classroom.grade
                if classroom
                else None
            ),

            "stream": (
                classroom.stream
                if classroom
                else None
            ),

            "class_teacher": (
                teacher.user.get_full_name()
                if teacher
                else None
            ),

            "teacher_phone": (
                teacher.user.phone_number
                if teacher
                else None
            ),

            "relationship": "Parent",

            "date_admitted": (
                student.date_admitted
            ),

            "status": student.status,

            "attendance_percentage": (
                attendance_percentage
            ),

            "latest_grade": (
                latest_result.overall_grade
                if latest_result
                else "-"
            ),

            "fee_balance": fee_balance,
        }

        serializer = ParentChildDetailsSerializer(data)

        return Response(serializer.data)


# ============================================================
# TEACHER DASHBOARD
# ============================================================

class TeacherDashboardAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def get(self, request):

        teacher = request.user.teacher_profile

        assignments = TeacherAssignment.objects.filter(
            teacher=teacher,
            is_active=True,
        )

        assigned_classes = (
            assignments
            .values("classroom")
            .distinct()
            .count()
        )

        assigned_subjects = (
            assignments
            .values("subject")
            .distinct()
            .count()
        )

        total_students = (
            Student.objects
            .filter(
                classroom__in=assignments.values(
                    "classroom"
                )
            )
            .distinct()
            .count()
        )

        today = timezone.localdate().strftime(
            "%A"
        )

        today_lessons = Timetable.objects.filter(
            assignment__teacher=teacher,
            day=today,
            is_active=True,
        ).count()

        pending_results = (
            ResultSubmission.objects
            .filter(
                submitted_by=request.user,
                approval_status__in=[
                    ResultSubmission.ApprovalStatus.DRAFT,
                    ResultSubmission.ApprovalStatus.RETURNED,
                ],
            )
            .count()
        )

        data = {
            "teacher_name": (
                request.user.get_full_name()
            ),

            "is_class_teacher": (
                is_class_teacher(request.user)
            ),

            "assigned_classes": assigned_classes,

            "assigned_subjects": assigned_subjects,

            "total_students": total_students,

            "today_lessons": today_lessons,

            "pending_results": pending_results,
        }

        serializer = TeacherDashboardSerializer(data)

        return Response(serializer.data)


# ============================================================
# TEACHER STUDENTS
# ============================================================

class TeacherStudentsAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def get(self, request):

        teacher = request.user.teacher_profile

        assignments = TeacherAssignment.objects.filter(
            teacher=teacher,
            is_active=True,
        )

        classroom_ids = (
            assignments
            .values_list(
                "classroom",
                flat=True,
            )
            .distinct()
        )

        students = (
            Student.objects
            .filter(
                classroom__in=classroom_ids
            )
            .select_related(
                "classroom",
                "parent",
            )
            .order_by(
                "classroom__grade",
                "last_name",
                "first_name",
            )
        )

        data = []

        for student in students:

            attendance = Attendance.objects.filter(
                student=student
            )

            total = attendance.count()

            present = attendance.filter(
                status=Attendance.Status.PRESENT
            ).count()

            attendance_percentage = (
                round(
                    (present / total) * 100,
                    2,
                )
                if total > 0
                else 0
            )

            latest_result = (
                StudentTermResult.objects
                .filter(student=student)
                .order_by("-id")
                .first()
            )

            data.append({
                "id": student.id,

                "photo": (
                    student.photo.url
                    if student.photo
                    else None
                ),

                "admission_number": (
                    student.admission_number
                ),

                "assessment_number": (
                    student.assessment_number
                ),

                "first_name": student.first_name,
                "last_name": student.last_name,

                "grade": (
                    student.classroom.grade
                    if student.classroom
                    else None
                ),

                "stream": (
                    student.classroom.stream
                    if student.classroom
                    else None
                ),

                "attendance_percentage": (
                    attendance_percentage
                ),

                "latest_grade": (
                    latest_result.overall_grade
                    if latest_result
                    else "-"
                ),

                "status": student.status,
            })

        serializer = TeacherStudentSerializer(
            data,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# TEACHER STUDENT DETAILS
# ============================================================

class TeacherStudentDetailsAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def get(self, request, pk):

        teacher = request.user.teacher_profile

        classroom_ids = (
            TeacherAssignment.objects
            .filter(
                teacher=teacher,
                is_active=True,
            )
            .values_list(
                "classroom_id",
                flat=True,
            )
        )

        student = get_object_or_404(
            Student.objects.select_related(
                "classroom",
                "parent__user",
            ),
            pk=pk,
            classroom_id__in=classroom_ids,
        )

        parent_name = None
        parent_phone = None

        if student.parent and student.parent.user:

            parent_name = (
                student.parent.user.get_full_name()
                or student.parent.user.username
            )

            parent_phone = (
                student.parent.user.phone_number
            )

        attendance = Attendance.objects.filter(
            student=student
        )

        attendance_total = attendance.count()

        attendance_present = attendance.filter(
            status=Attendance.Status.PRESENT
        ).count()

        attendance_percentage = (
            round(
                (
                    attendance_present
                    / attendance_total
                ) * 100,
                2,
            )
            if attendance_total > 0
            else 0
        )

        latest_result = (
            StudentTermResult.objects
            .filter(student=student)
            .order_by("-id")
            .first()
        )

        fee_balance = (
            StudentFee.objects
            .filter(student=student)
            .aggregate(
                balance=Sum("balance")
            )["balance"]
            or Decimal("0.00")
        )

        data = {
            "id": student.id,

            "photo": (
                student.photo.url
                if student.photo
                else None
            ),

            "admission_number": (
                student.admission_number
            ),

            "assessment_number": (
                student.assessment_number
            ),

            "first_name": student.first_name,
            "last_name": student.last_name,
            "gender": student.gender,

            "date_of_birth": (
                student.date_of_birth
            ),

            "grade": (
                student.classroom.grade
                if student.classroom
                else None
            ),

            "stream": (
                student.classroom.stream
                if student.classroom
                else None
            ),

            "date_admitted": (
                student.date_admitted
            ),

            "status": student.status,

            "parent_name": parent_name,
            "parent_phone": parent_phone,

            "attendance_percentage": (
                attendance_percentage
            ),

            "latest_grade": (
                latest_result.overall_grade
                if latest_result
                else "-"
            ),

            "fee_balance": fee_balance,

            "class_teacher": is_class_teacher(
                request.user
            ),
        }

        serializer = TeacherStudentDetailsSerializer(
            data
        )

        return Response(serializer.data)


# ============================================================
# TEACHER STUDENT RESULTS
# ============================================================

class TeacherStudentResultsAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def get(self, request, pk):

        teacher = request.user.teacher_profile

        classroom_ids = (
            TeacherAssignment.objects
            .filter(
                teacher=teacher,
                is_active=True,
            )
            .values_list(
                "classroom_id",
                flat=True,
            )
        )

        student = get_object_or_404(
            Student,
            pk=pk,
            classroom_id__in=classroom_ids,
        )

        results = (
            StudentResult.objects
            .filter(student=student)
            .select_related(
                "subject",
                "grade",
            )
            .order_by(
                "subject__name"
            )
        )

        data = []

        for result in results:

            data.append({
                "id": result.id,

                "subject": (
                    result.subject.name
                ),

                "score": (
                    result.average_score
                ),

                "grade": (
                    result.grade.level
                    if result.grade
                    else "-"
                ),

                "cbc_code": (
                    result.cbc_code
                ),

                "description": (
                    result.cbc_description
                ),
            })

        return Response(data)


# ============================================================
# TEACHER UPDATE STUDENT RESULT
# ============================================================

class TeacherUpdateStudentResultAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def patch(self, request, pk):

        result = get_object_or_404(
            StudentResult,
            pk=pk,
        )

        teacher = request.user.teacher_profile

        assignment_exists = (
            TeacherAssignment.objects
            .filter(
                teacher=teacher,
                subject=result.subject,
                classroom=result.classroom,
                is_active=True,
            )
            .exists()
        )

        if not assignment_exists:
            return Response(
                {
                    "detail": (
                        "You are not assigned to "
                        "teach this subject."
                    )
                },
                status=403,
            )

        serializer = (
            TeacherStudentResultUpdateSerializer(
                result,
                data=request.data,
                partial=True,
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data
        )


# ============================================================
# TEACHER ASSESSMENTS
# ============================================================

class TeacherAssessmentListAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def get(self, request):

        teacher = request.user.teacher_profile

        assignments = TeacherAssignment.objects.filter(
            teacher=teacher,
            is_active=True,
        )

        classroom_ids = assignments.values(
            "classroom"
        )

        subject_ids = assignments.values(
            "subject"
        )

        assessments = (
            Assessment.objects
            .filter(
                classroom__in=classroom_ids,
                subject__in=subject_ids,
            )
            .select_related(
                "classroom",
                "subject",
            )
            .order_by(
                "-assessment_date"
            )
        )

        data = []

        for assessment in assessments:

            assessment_type = getattr(
                assessment,
                "assessment_type",
                None,
            )

            if hasattr(
                assessment_type,
                "name",
            ):
                assessment_type_name = (
                    assessment_type.name
                )
            else:
                assessment_type_name = (
                    assessment_type
                    if assessment_type
                    else "-"
                )

            data.append({
                "id": assessment.id,

                "assessment_type": (
                    assessment_type_name
                ),

                "subject": (
                    assessment.subject.name
                ),

                "classroom": str(
                    assessment.classroom
                ),

                "term": getattr(
                    assessment,
                    "term",
                    None,
                ),

                "academic_year": getattr(
                    assessment,
                    "academic_year",
                    None,
                ),

                "assessment_date": getattr(
                    assessment,
                    "assessment_date",
                    None,
                ),

                "total_marks": getattr(
                    assessment,
                    "total_marks",
                    None,
                ),
            })

        return Response(data)


# ============================================================
# ASSESSMENT DETAILS / MARK ENTRY
# ============================================================

class TeacherAssessmentDetailsAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def get(self, request, pk):

        assessment = get_object_or_404(
            Assessment.objects.select_related(
                "classroom",
                "subject",
            ),
            pk=pk,
        )

        teacher = request.user.teacher_profile

        is_assigned = TeacherAssignment.objects.filter(
            teacher=teacher,
            classroom=assessment.classroom,
            subject=assessment.subject,
            is_active=True,
        ).exists()

        if not is_assigned:
            return Response(
                {
                    "detail": (
                        "You are not assigned to "
                        "this class/subject."
                    )
                },
                status=403,
            )

        students = (
            Student.objects
            .filter(
                classroom=assessment.classroom
            )
            .order_by(
                "first_name",
                "last_name",
            )
        )

        data = []

        for student in students:

            data.append({
                "student_id": student.id,

                "admission_number": (
                    student.admission_number
                ),

                "student_name": (
                    f"{student.first_name} "
                    f"{student.last_name}"
                ),

                "marks": "",

                "status": "Pending",
            })

        assessment_type = getattr(
            assessment,
            "assessment_type",
            None,
        )

        if hasattr(
            assessment_type,
            "name",
        ):
            assessment_type = (
                assessment_type.name
            )

        return Response({
            "assessment": {
                "id": assessment.id,

                "subject": (
                    assessment.subject.name
                ),

                "assessment_type": (
                    assessment_type
                    if assessment_type
                    else "-"
                ),

                "classroom": str(
                    assessment.classroom
                ),

                "term": getattr(
                    assessment,
                    "term",
                    None,
                ),

                "academic_year": getattr(
                    assessment,
                    "academic_year",
                    None,
                ),

                "total_marks": getattr(
                    assessment,
                    "total_marks",
                    None,
                ),
            },

            "students": data,
        })


# ============================================================
# SAVE ASSESSMENT MARKS
# ============================================================

class TeacherSaveAssessmentMarksAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTeacher,
    ]

    def post(self, request, pk):

        assessment = get_object_or_404(
            Assessment.objects.select_related(
                "classroom",
                "subject",
            ),
            pk=pk,
        )

        teacher = getattr(
            request.user,
            "teacher_profile",
            None,
        )

        is_assigned = (
            bool(teacher)
            and TeacherAssignment.objects.filter(
                teacher=teacher,
                classroom=assessment.classroom,
                subject=assessment.subject,
                is_active=True,
            ).exists()
        )

        if not is_assigned:
            return Response(
                {
                    "detail": (
                        "You are not assigned to "
                        "this class/subject."
                    )
                },
                status=403,
            )

        submission, _ = (
            ResultSubmission.objects.get_or_create(
                assessment=assessment,
                defaults={
                    "submitted_by": request.user
                },
            )
        )

        from results.services import (
            get_grade,
            calculate_percentage,
            process_result,
        )

        students_data = request.data.get(
            "students",
            []
        )

        if not isinstance(
            students_data,
            list,
        ):
            return Response(
                {
                    "detail": (
                        "students must be a list."
                    )
                },
                status=400,
            )

        for item in students_data:

            student_id = item.get(
                "student_id"
            )

            marks = item.get(
                "marks"
            )

            if not student_id:
                continue

            student = get_object_or_404(
                Student,
                pk=student_id,
                classroom=assessment.classroom,
            )

            if marks in [
                "",
                None,
            ]:
                continue

            try:
                marks = Decimal(
                    str(marks)
                )
            except (
                ValueError,
                TypeError,
            ):
                return Response(
                    {
                        "detail": (
                            f"Invalid marks for "
                            f"{student.first_name} "
                            f"{student.last_name}."
                        )
                    },
                    status=400,
                )

            total_marks = (
                assessment.total_marks
                or 100
            )

            if marks < 0:
                return Response(
                    {
                        "detail": (
                            "Marks cannot be negative."
                        )
                    },
                    status=400,
                )

            if marks > total_marks:
                return Response(
                    {
                        "detail": (
                            f"Marks cannot exceed "
                            f"{total_marks}."
                        )
                    },
                    status=400,
                )

            percentage = calculate_percentage(
                marks,
                total_marks,
            )

            grade_scale = get_grade(
                percentage
            )

            result, _ = (
                Result.objects.update_or_create(
                    submission=submission,
                    student=student,
                    defaults={
                        "marks": marks,

                        "weighted_marks": (
                            percentage
                        ),

                        "grade": grade_scale,

                        "cbc_code": (
                            grade_scale.level
                            if grade_scale
                            else ""
                        ),

                        "cbc_description": (
                            grade_scale.description
                            if grade_scale
                            else ""
                        ),

                        "entered_by": (
                            request.user
                        ),

                        "last_modified_by": (
                            request.user
                        ),

                        "status": (
                            Result.ResultStatus.PRESENT
                        ),
                    },
                )
            )

            process_result(result)

        return Response({
            "message": (
                "Marks saved successfully."
            )
        })


# ============================================================
# PARENT REPORT CARDS
# ============================================================

class ParentReportCardsAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        parent = ParentProfile.objects.filter(
            user=request.user
        ).first()

        if not parent:
            return Response(
                {
                    "detail": (
                        "Parent profile not found."
                    )
                },
                status=404,
            )

        students = (
            Student.objects
            .filter(parent=parent)
            .select_related("classroom")
        )

        term_results = (
            StudentTermResult.objects
            .filter(
                student__in=students
            )
            .select_related(
                "student",
                "student__classroom",
            )
            .order_by(
                "-academic_year",
                "-term",
                "student__first_name",
                "student__last_name",
            )
        )

        data = []

        for result in term_results:

            student = result.student
            classroom = student.classroom

            overall_grade = getattr(
                result,
                "overall_grade",
                None,
            )

            grade_letter = "-"

            if overall_grade:

                if hasattr(
                    overall_grade,
                    "level",
                ):
                    grade_letter = (
                        overall_grade.level
                    )

                else:
                    grade_letter = str(
                        overall_grade
                    )

            data.append({

                "student_id": student.id,

                "first_name": (
                    student.first_name
                ),

                "last_name": (
                    student.last_name
                ),

                "photo": student.photo,

                "admission_number": (
                    student.admission_number
                ),

                "assessment_number": (
                    student.assessment_number
                ),

                "grade": (
                    classroom.grade
                    if classroom
                    else ""
                ),

                "stream": (
                    classroom.stream
                    if classroom
                    else ""
                ),

                "academic_year": (
                    result.academic_year
                ),

                "term": result.term,

                "average_score": getattr(
                    result,
                    "average_marks",
                    None,
                ),

                "grade_letter": grade_letter,

                "total_marks": getattr(
                    result,
                    "total_marks",
                    None,
                ),

                "total_subjects": getattr(
                    result,
                    "total_subjects",
                    None,
                ),

                "position": getattr(
                    result,
                    "position",
                    None,
                ),

                "attendance_percentage": getattr(
                    result,
                    "attendance_percentage",
                    None,
                ),

                "class_teacher_comment": getattr(
                    result,
                    "class_teacher_comment",
                    "",
                ),

                "headteacher_comment": getattr(
                    result,
                    "headteacher_comment",
                    "",
                ),
            })

        return Response(data)