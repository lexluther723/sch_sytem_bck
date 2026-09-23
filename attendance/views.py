from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardResultsSetPagination

from accounts.models import (
    CustomUser,
    TeacherProfile,
    ParentProfile,
)

from assignments.models import TeacherAssignment

from notifiations.services import create_notification

from students.models import Student

from attendance.models import (
    Attendance,
    AttendanceSubmission,
)

from attendance.serializers import (
    BulkAttendanceSerializer,
    CreateAttendanceSubmissionSerializer,
    AttendanceDetailSerializer,
    StudentAttendanceHistorySerializer,
)

from attendance.permissions import (
    IsAssignedClassTeacher,
)


# ============================================================
# HELPER — GET TEACHER PROFILE
# ============================================================

def get_teacher_profile(request):
    """
    Safely return the TeacherProfile belonging to the
    currently authenticated user.
    """

    try:
        return request.user.teacher_profile

    except TeacherProfile.DoesNotExist:
        return None

    except Exception:
        return None


# ============================================================
# HELPER — VERIFY CLASS TEACHER ASSIGNMENT
# ============================================================

def verify_class_teacher(request, assignment):
    """
    Verify that:

    1. Logged-in user is a teacher who owns this assignment
       as an active class teacher — OR the user is a Super
       Admin / Academic Coordinator.
    2. Assignment is active.
    """

    user = request.user

    # --------------------------------------------------------
    # ADMIN / COORDINATOR OVERRIDE
    # --------------------------------------------------------

    if user.role in [
        CustomUser.Role.SUPER_ADMIN,
        CustomUser.Role.ACADEMIC_COORDINATOR,
    ]:

        if not assignment.is_active:
            return (
                None,
                Response(
                    {
                        "error": (
                            "This teaching assignment "
                            "is inactive."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        return None, None

    # --------------------------------------------------------
    # TEACHER PROFILE
    # --------------------------------------------------------

    teacher_profile = get_teacher_profile(request)

    if not teacher_profile:
        return (
            None,
            Response(
                {
                    "error": (
                        "Only teachers can access "
                        "attendance."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            ),
        )

    # --------------------------------------------------------
    # Teacher must own assignment
    # --------------------------------------------------------

    if assignment.teacher_id != teacher_profile.id:
        return (
            None,
            Response(
                {
                    "error": (
                        "This assignment does not "
                        "belong to you."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            ),
        )

    # --------------------------------------------------------
    # Must be class teacher
    # --------------------------------------------------------

    if not assignment.is_class_teacher:
        return (
            None,
            Response(
                {
                    "error": (
                        "Only the class teacher can "
                        "mark attendance for this class."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            ),
        )

    # --------------------------------------------------------
    # Assignment must be active
    # --------------------------------------------------------

    if not assignment.is_active:
        return (
            None,
            Response(
                {
                    "error": (
                        "This teaching assignment "
                        "is inactive."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            ),
        )

    return teacher_profile, None


# ============================================================
# CREATE ATTENDANCE SUBMISSION
# ============================================================

class AttendanceSubmissionCreateView(APIView):

    permission_classes = [
        IsAssignedClassTeacher
    ]

    @transaction.atomic
    def post(self, request):

        serializer = CreateAttendanceSubmissionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        assignment_id = serializer.validated_data[
            "assignment"
        ]

        assignment = get_object_or_404(
            TeacherAssignment.objects.select_related(
                "teacher",
                "classroom",
                "subject",
            ),
            pk=assignment_id,
        )

        (
            teacher_profile,
            error_response,
        ) = verify_class_teacher(
            request,
            assignment,
        )

        if error_response:
            return error_response

        today = timezone.localdate()

        submission, created = (
            AttendanceSubmission.objects.get_or_create(

                assignment=assignment,

                date=today,

                defaults={
                    "classroom": assignment.classroom,
                    "submitted_by": request.user,
                    "status": (
                        AttendanceSubmission.Status.DRAFT
                    ),
                },
            )
        )

        if submission.classroom_id != assignment.classroom_id:

            submission.classroom = assignment.classroom

            submission.save(
                update_fields=[
                    "classroom"
                ]
            )

        return Response(
            {
                "submission": submission.id,
                "created": created,
                "assignment": assignment.id,

                "classroom": str(
                    assignment.classroom
                ),

                "classroom_id":
                    assignment.classroom_id,

                "subject": (
                    assignment.subject.name
                    if assignment.subject
                    else ""
                ),

                "subject_id":
                    assignment.subject_id,

                "date":
                    submission.date,

                "status":
                    submission.status,

                "is_class_teacher":
                    assignment.is_class_teacher,
            },

            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


# ============================================================
# MARK ATTENDANCE
# ============================================================

class MarkAttendanceView(APIView):

    permission_classes = [
        IsAssignedClassTeacher
    ]

    # ========================================================
    # GET — LOAD STUDENTS
    # ========================================================

    @transaction.atomic
    def get(self, request):

        assignment_id = request.query_params.get(
            "assignment"
        )

        if not assignment_id:

            return Response(
                {
                    "error": "Assignment is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment = get_object_or_404(
            TeacherAssignment.objects.select_related(
                "teacher",
                "classroom",
                "subject",
            ),
            pk=assignment_id,
        )

        (
            teacher_profile,
            error_response,
        ) = verify_class_teacher(
            request,
            assignment,
        )

        if error_response:
            return error_response

        today = timezone.localdate()

        submission, created = (
            AttendanceSubmission.objects.get_or_create(

                assignment=assignment,

                date=today,

                defaults={
                    "classroom": assignment.classroom,
                    "submitted_by": request.user,
                    "status":
                        AttendanceSubmission.Status.DRAFT,
                },
            )
        )

        students = (
            Student.objects
            .filter(
                classroom=assignment.classroom
            )
            .order_by(
                "admission_number",
                "first_name",
                "last_name",
            )
        )

        records = []

        for student in students:

            attendance, created_record = (
                Attendance.objects.get_or_create(

                    submission=submission,

                    student=student,

                    defaults={
                        "status":
                            Attendance.Status.PRESENT,

                        "remarks": "",
                    },
                )
            )

            records.append(
                {
                    "id": attendance.id,

                    "student":
                        student.id,

                    "admission_number":
                        student.admission_number,

                    "name": (
                        f"{student.first_name} "
                        f"{student.last_name}"
                    ).strip(),

                    "status":
                        attendance.status,

                    "remarks":
                        attendance.remarks or "",
                }
            )

        return Response(
            {
                "submission":
                    submission.id,

                "assignment":
                    assignment.id,

                "classroom":
                    str(assignment.classroom),

                "classroom_id":
                    assignment.classroom_id,

                "subject": (
                    assignment.subject.name
                    if assignment.subject
                    else ""
                ),

                "subject_id":
                    assignment.subject_id,

                "date":
                    submission.date,

                "status":
                    submission.status,

                "created":
                    created,

                "is_class_teacher":
                    assignment.is_class_teacher,

                "students":
                    records,
            },

            status=status.HTTP_200_OK,
        )

    # ========================================================
    # POST — SAVE ATTENDANCE
    #
    # ONE CLICK:
    #
    # 1. Save attendance
    # 2. Finalize attendance
    # 3. Find parent
    # 4. Create parent notification
    #
    # NO APPROVAL
    # NO SECOND BUTTON
    # ========================================================

    @transaction.atomic
    def post(self, request):

        serializer = BulkAttendanceSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        submission = get_object_or_404(

            AttendanceSubmission.objects
            .select_for_update()
            .select_related(
                "assignment",
                "classroom",
                "assignment__teacher",
                "assignment__subject",
            ),

            pk=serializer.validated_data[
                "submission"
            ],
        )

        # ----------------------------------------------------
        # Admin / Coordinator override
        # ----------------------------------------------------

        is_admin_or_coordinator = request.user.role in [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
        ]

        teacher_profile = get_teacher_profile(
            request
        )

        if not teacher_profile and not is_admin_or_coordinator:

            return Response(
                {
                    "error": (
                        "Only teachers can "
                        "save attendance."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # Assignment
        # ----------------------------------------------------

        assignment = submission.assignment

        if not assignment:

            return Response(
                {
                    "error": (
                        "This attendance submission "
                        "has no teaching assignment."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Teacher ownership / class teacher
        # ----------------------------------------------------

        if not is_admin_or_coordinator:

            if assignment.teacher_id != teacher_profile.id:

                return Response(
                    {
                        "error": (
                            "This attendance submission "
                            "does not belong to you."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not assignment.is_class_teacher:

                return Response(
                    {
                        "error": (
                            "Only the class teacher can "
                            "save attendance for this class."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # ----------------------------------------------------
        # Active assignment
        # ----------------------------------------------------

        if not assignment.is_active:

            return Response(
                {
                    "error": "This assignment is inactive."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        attendance_date = submission.date

        teacher_name = (
            request.user.get_full_name()
            or request.user.username
        )

        saved_records = []

        notifications_sent = 0

        parents_notified = []

        students_without_parent = []

        notification_errors = []

        notifications_already_exist = []

        # ====================================================
        # SAVE EACH STUDENT
        # ====================================================

        for record in serializer.validated_data[
            "records"
        ]:

            student = get_object_or_404(
                Student.objects.select_related(
                    "parent",
                    "parent__user",
                ),
                pk=record["student"],
            )

            # ------------------------------------------------
            # SECURITY
            # ------------------------------------------------

            if (
                student.classroom_id
                != submission.classroom_id
            ):

                return Response(
                    {
                        "error": (
                            f"{student.first_name} "
                            f"{student.last_name} "
                            "does not belong to this "
                            "classroom."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_status = record["status"]

            new_remarks = (
                record.get("remarks")
                or ""
            ).strip()

            attendance, created_record = (
                Attendance.objects.update_or_create(

                    submission=submission,

                    student=student,

                    defaults={
                        "status": new_status,
                        "remarks": new_remarks,
                    },
                )
            )

            saved_records.append(
                {
                    "id":
                        attendance.id,

                    "student":
                        student.id,

                    "student_name": (
                        f"{student.first_name} "
                        f"{student.last_name}"
                    ).strip(),

                    "status":
                        attendance.status,

                    "remarks":
                        attendance.remarks or "",
                }
            )

            # =================================================
            # ONLY ABSENT / EXCUSED NOTIFY PARENTS
            # =================================================

            if attendance.status == Attendance.Status.PRESENT:
                continue

            # =================================================
            # FIND PARENT
            # =================================================

            parent_profile = getattr(
                student,
                "parent",
                None,
            )

            if not parent_profile:

                students_without_parent.append(
                    {
                        "student_id":
                            student.id,

                        "student_name": (
                            f"{student.first_name} "
                            f"{student.last_name}"
                        ).strip(),

                        "admission_number":
                            student.admission_number,

                        "reason":
                            "Student has no parent profile.",
                    }
                )

                continue

            parent_user = getattr(
                parent_profile,
                "user",
                None,
            )

            if not parent_user:

                students_without_parent.append(
                    {
                        "student_id":
                            student.id,

                        "student_name": (
                            f"{student.first_name} "
                            f"{student.last_name}"
                        ).strip(),

                        "admission_number":
                            student.admission_number,

                        "reason":
                            "ParentProfile has no user.",
                    }
                )

                continue

            # =================================================
            # BUILD NOTIFICATION
            # =================================================

            title = (
                "Attendance: "
                f"{student.first_name} — "
                f"{attendance.status}"
            )

            message = (
                "Dear Parent, your child "
                f"{student.first_name} "
                f"{student.last_name} "
                "was marked as "
                f"{attendance.status} "
                f"on {attendance_date}. "
                f"Marked by: {teacher_name}."
            )

            if attendance.remarks:

                message += (
                    " Remarks: "
                    f"{attendance.remarks}"
                )

            # =================================================
            # PREVENT DUPLICATE NOTIFICATION
            # =================================================

            existing_notification = (
                attendance.notifications
                .filter(
                    recipient=parent_user,
                    notification_type="Attendance",
                    title=title,
                )
                .first()
            )

            if existing_notification:

                notifications_already_exist.append(
                    {
                        "student_id":
                            student.id,

                        "student_name": (
                            f"{student.first_name} "
                            f"{student.last_name}"
                        ).strip(),

                        "parent_id":
                            parent_user.id,

                        "parent_username":
                            parent_user.username,

                        "notification_id":
                            existing_notification.id,

                        "status":
                            attendance.status,
                    }
                )

                continue

            # =================================================
            # CREATE NOTIFICATION
            # =================================================

            try:

                notification = create_notification(

                    recipient=parent_user,

                    triggered_by=request.user,

                    attendance=attendance,

                    title=title,

                    message=message,

                    notification_type="Attendance",
                )

                notifications_sent += 1

                parents_notified.append(
                    {
                        "parent_id":
                            parent_user.id,

                        "parent_username":
                            parent_user.username,

                        "student_id":
                            student.id,

                        "student_name": (
                            f"{student.first_name} "
                            f"{student.last_name}"
                        ).strip(),

                        "notification_id":
                            notification.id,

                        "attendance_id":
                            attendance.id,

                        "attendance_status":
                            attendance.status,
                    }
                )

            except Exception as notification_error:

                notification_errors.append(
                    {
                        "student_id":
                            student.id,

                        "student_name": (
                            f"{student.first_name} "
                            f"{student.last_name}"
                        ).strip(),

                        "parent_id":
                            parent_user.id,

                        "parent_username":
                            parent_user.username,

                        "error":
                            str(notification_error),
                    }
                )

        # ====================================================
        # FINALIZE IMMEDIATELY
        # ====================================================

        submission.status = (
            AttendanceSubmission.Status.FINAL
        )

        submission.submitted_by = request.user

        submission.submitted_at = timezone.now()

        submission.save(
            update_fields=[
                "status",
                "submitted_by",
                "submitted_at",
                "updated_at",
            ]
        )

        # ====================================================
        # FINAL RESPONSE
        # ====================================================

        return Response(
            {
                "message":
                    "Attendance marked successfully.",

                "submission":
                    submission.id,

                "classroom":
                    str(submission.classroom),

                "date":
                    submission.date,

                "status":
                    submission.status,

                "saved_records":
                    saved_records,

                "notifications_sent":
                    notifications_sent,

                "parent_notified":
                    notifications_sent > 0,

                "parents_notified":
                    parents_notified,

                "students_without_parent":
                    students_without_parent,

                "notification_errors":
                    notification_errors,

                "notifications_already_exist":
                    notifications_already_exist,

                "notification_summary": {

                    "sent":
                        notifications_sent,

                    "already_exists":
                        len(
                            notifications_already_exist
                        ),

                    "students_without_parent":
                        len(
                            students_without_parent
                        ),

                    "notification_errors":
                        len(
                            notification_errors
                        ),
                },
            },

            status=status.HTTP_200_OK,
        )


# ============================================================
# SUBMIT ATTENDANCE
#
# KEPT FOR BACKWARD COMPATIBILITY.
#
# React DOES NOT need to call this.
# ============================================================

class SubmitAttendanceView(APIView):

    permission_classes = [
        IsAssignedClassTeacher
    ]

    @transaction.atomic
    def post(self, request):

        submission_id = request.data.get(
            "submission"
        )

        if not submission_id:

            return Response(
                {
                    "error": (
                        "Attendance is saved directly "
                        "when marked. A separate submit "
                        "step is not required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = get_object_or_404(
            AttendanceSubmission,
            pk=submission_id,
        )

        teacher_profile = get_teacher_profile(
            request
        )

        if not teacher_profile:

            return Response(
                {
                    "error": (
                        "Only teachers can access "
                        "attendance."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = submission.assignment

        if (
            not assignment
            or assignment.teacher_id
            != teacher_profile.id
        ):

            return Response(
                {
                    "error": (
                        "This attendance submission "
                        "does not belong to you."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "message": (
                    "Attendance is already saved "
                    "automatically. No approval or "
                    "submit step is required."
                ),

                "submission":
                    submission.id,

                "status":
                    submission.status,
            },

            status=status.HTTP_200_OK,
        )


# ============================================================
# ATTENDANCE DETAIL
#
# ADMIN / ACADEMIC COORDINATOR
# ============================================================

class AttendanceDetailView(APIView):

    def get(
        self,
        request,
        submission_id,
    ):

        if request.user.role not in [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
        ]:

            return Response(
                {
                    "error": "Access denied."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        submission = get_object_or_404(

            AttendanceSubmission.objects.select_related(
                "classroom",
                "submitted_by",
                "assignment",
                "assignment__teacher",
                "assignment__subject",
            ),

            pk=submission_id,
        )

        records = (
            Attendance.objects
            .filter(
                submission=submission
            )
            .select_related(
                "student"
            )
        )

        serializer = AttendanceDetailSerializer(
            records,
            many=True,
        )

        return Response(
            {
                "submission":
                    submission.id,

                "assignment":
                    submission.assignment_id,

                "classroom":
                    str(submission.classroom),

                "date":
                    submission.date,

                "status":
                    submission.status,

                "attendance":
                    serializer.data,
            },

            status=status.HTTP_200_OK,
        )


# ============================================================
# STUDENT ATTENDANCE HISTORY
# ============================================================

class StudentAttendanceHistoryView(APIView):

    def get(
        self,
        request,
        student_id,
    ):

        student = get_object_or_404(

            Student.objects.select_related(
                "classroom",
                "parent",
                "parent__user",
            ),

            pk=student_id,
        )

        # ----------------------------------------------------
        # SECURITY
        # ----------------------------------------------------

        user = request.user

        is_admin_or_coordinator = user.role in [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
        ]

        is_owning_parent = False

        if user.role == CustomUser.Role.PARENT:

            try:

                parent_profile = user.parent_profile

                is_owning_parent = (
                    parent_profile.children
                    .filter(id=student.id)
                    .exists()
                )

            except ParentProfile.DoesNotExist:

                is_owning_parent = False

        is_assigned_teacher = False

        if user.role == CustomUser.Role.TEACHER:

            try:

                teacher_profile = user.teacher_profile

                is_assigned_teacher = (
                    TeacherAssignment.objects
                    .filter(
                        teacher=teacher_profile,
                        classroom=student.classroom,
                        is_active=True,
                    )
                    .exists()
                )

            except TeacherProfile.DoesNotExist:

                is_assigned_teacher = False

        if not (
            is_admin_or_coordinator
            or is_owning_parent
            or is_assigned_teacher
        ):

            return Response(
                {
                    "error": (
                        "You do not have permission to view "
                        "this student's attendance history."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        records = (
            Attendance.objects
            .filter(
                student=student,

                submission__status=(
                    AttendanceSubmission.Status.FINAL
                ),
            )
            .select_related(
                "submission",
                "submission__classroom",
            )
            .order_by(
                "-submission__date"
            )
        )

        # ----------------------------------------------------
        # FILTERS
        # ----------------------------------------------------

        status_param = request.query_params.get(
            "status"
        )

        start_date = request.query_params.get(
            "start_date"
        )

        end_date = request.query_params.get(
            "end_date"
        )

        if status_param:

            records = records.filter(
                status=status_param
            )

        if start_date:

            records = records.filter(
                submission__date__gte=start_date
            )

        if end_date:

            records = records.filter(
                submission__date__lte=end_date
            )

        # ----------------------------------------------------
        # SUMMARY COUNTS
        #
        # BEFORE: 4 separate `.count()` queries against the same
        # filtered queryset (total / present / absent / excused) —
        # 4 round trips to the database to compute numbers the DB
        # can produce in one pass.
        #
        # AFTER: one `.aggregate()` call using conditional `Count`
        # expressions, so the database computes all four numbers in
        # a single query instead of Django re-issuing the base
        # filter four times.
        # ----------------------------------------------------
        summary_counts = records.aggregate(
            total=Count("id"),
            present=Count(
                "id", filter=Q(status=Attendance.Status.PRESENT)
            ),
            absent=Count(
                "id", filter=Q(status=Attendance.Status.ABSENT)
            ),
            excused=Count(
                "id", filter=Q(status=Attendance.Status.EXCUSED)
            ),
        )

        total = summary_counts["total"]
        present = summary_counts["present"]
        attendance_percentage = (
            round((present / total) * 100, 2) if total > 0 else 0
        )

        # ----------------------------------------------------
        # PAGINATE THE RECORD LIST
        #
        # BEFORE: `records` (every attendance entry for this
        # student since enrollment — potentially years of daily
        # records) was serialized in full in one response.
        #
        # AFTER: only the requested page of records is serialized.
        # Note the summary counts above are computed from the FULL
        # filtered queryset (via .aggregate(), before pagination
        # slices it), so "attendance_percentage" still reflects the
        # whole filtered date range even though only one page of
        # rows is returned — pagination changes how much of the
        # LIST is returned, not what the summary means.
        # ----------------------------------------------------
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(records, request, view=self)
        serializer = StudentAttendanceHistorySerializer(page, many=True)

        # Note: we don't use `paginator.get_paginated_response()`
        # directly here because this endpoint's payload is a
        # {student, summary, attendance} object, not a bare list —
        # unlike a plain ListAPIView, "attendance" (the page of
        # records) is only one part of the response. We reuse the
        # SAME pagination metadata keys (count/total_pages/etc.) for
        # consistency with every other paginated endpoint, just
        # nested under the response instead of wrapping the whole
        # body.
        return Response(
            {
                "student": {
                    "id": student.id,
                    "admission_number": student.admission_number,
                    "name": (
                        f"{student.first_name} "
                        f"{student.last_name}"
                    ).strip(),
                    "classroom": str(student.classroom),
                },
                "summary": {
                    "total_days": total,
                    "present": present,
                    "absent": summary_counts["absent"],
                    "excused": summary_counts["excused"],
                    "attendance_percentage": attendance_percentage,
                },
                "count": paginator.page.paginator.count,
                "total_pages": paginator.page.paginator.num_pages,
                "current_page": paginator.page.number,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "attendance": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# TEACHER ATTENDANCE HISTORY
# ============================================================
class TeacherAttendanceHistoryView(APIView):

    permission_classes = [
        IsAssignedClassTeacher
    ]

    def get(
        self,
        request,
    ):

        teacher_profile = get_teacher_profile(
            request
        )

        if not teacher_profile:

            return Response(
                {
                    "error": (
                        "Only teachers can view "
                        "attendance history."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        records = (
            Attendance.objects
            .filter(
                submission__submitted_by=request.user
            )
            .select_related(
                "student",
                "submission",
                "submission__classroom",

                # ==========================================
                # GET ASSIGNMENT
                # ==========================================

                "submission__assignment",

                # ==========================================
                # GET SUBJECT
                # ==========================================

                "submission__assignment__subject",

                # ==========================================
                # GET CLASS TEACHER
                # TeacherAssignment.teacher
                # TeacherProfile.user
                # ==========================================

                "submission__assignment__teacher",
                "submission__assignment__teacher__user",

                # FIX (N+1): the loop below reads
                # `record.submission.submitted_by` for every row to
                # build "marked_by_name" — this FK was NOT in the
                # original select_related, so every single record in
                # the list triggered its own extra query just to
                # fetch who marked attendance that day.
                "submission__submitted_by",
            )
            .order_by(
                "-submission__date",
                "-id",
            )
        )

        # ----------------------------------------------------
        # FILTERS
        # ----------------------------------------------------

        classroom_id = request.query_params.get(
            "classroom"
        )

        status_param = request.query_params.get(
            "status"
        )

        start_date = request.query_params.get(
            "start_date"
        )

        end_date = request.query_params.get(
            "end_date"
        )

        if classroom_id:

            records = records.filter(
                submission__classroom_id=classroom_id
            )

        if status_param:

            records = records.filter(
                status=status_param
            )

        if start_date:

            records = records.filter(
                submission__date__gte=start_date
            )

        if end_date:

            records = records.filter(
                submission__date__lte=end_date
            )

        # BEFORE: this loop iterated over EVERY matching attendance
        # record a teacher has ever marked, building a Python dict
        # for each one, then returned the whole list in one
        # Response — for a teacher who has taught for several
        # terms, potentially tens of thousands of rows serialized
        # (and hand-built, row by row, in Python) per request.
        #
        # AFTER: paginate the queryset FIRST, then only loop over
        # (and only fetch related objects for) the current page.
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(records, request, view=self)

        data = []

        for record in page:

            # =================================================
            # STUDENT NAME
            # =================================================

            student_name = (
                f"{record.student.first_name or ''} "
                f"{record.student.last_name or ''}"
            ).strip()

            if not student_name:

                student_name = (
                    f"Student #{record.student_id}"
                )

            # =================================================
            # CLASSROOM
            # =================================================

            classroom_name = (
                str(
                    record.submission.classroom
                )
                if record.submission.classroom
                else "Unknown Class"
            )

            # =================================================
            # ASSIGNMENT
            # =================================================

            assignment = (
                record.submission.assignment
            )

            # =================================================
            # SUBJECT
            # =================================================

            subject_name = ""

            if (
                assignment
                and assignment.subject
            ):

                subject_name = (
                    assignment
                    .subject
                    .name
                )

            # =================================================
            # MARKED BY
            #
            # AttendanceSubmission.submitted_by
            # is the actual user who submitted attendance.
            # =================================================

            marked_by_name = ""

            marked_by_id = None

            submitted_by = (
                record.submission.submitted_by
            )

            if submitted_by:

                marked_by_id = submitted_by.id

                marked_by_name = (
                    submitted_by.get_full_name()
                    or submitted_by.username
                )

            # =================================================
            # CLASS TEACHER
            #
            # IMPORTANT:
            # We get this from TeacherAssignment,
            # NOT from /classes/.
            # =================================================

            class_teacher_name = ""

            class_teacher_id = None

            is_class_teacher = False

            if assignment:

                is_class_teacher = (
                    assignment.is_class_teacher
                )

                class_teacher = (
                    assignment.teacher
                )

                if class_teacher:

                    class_teacher_id = (
                        class_teacher.id
                    )

                    teacher_user = (
                        getattr(
                            class_teacher,
                            "user",
                            None,
                        )
                    )

                    if teacher_user:

                        class_teacher_name = (
                            teacher_user.get_full_name()
                            or teacher_user.username
                        )

                    # Fallbacks
                    if not class_teacher_name:

                        if getattr(
                            class_teacher,
                            "teacher_name",
                            None,
                        ):

                            class_teacher_name = (
                                class_teacher.teacher_name
                            )

                        elif getattr(
                            class_teacher,
                            "employee_number",
                            None,
                        ):

                            class_teacher_name = (
                                class_teacher.employee_number
                            )

            # =================================================
            # RESPONSE
            # =================================================

            data.append(
                {
                    "id":
                        record.id,

                    "submission":
                        record.submission.id,

                    "date":
                        record.submission.date,

                    "classroom_id":
                        record.submission.classroom_id,

                    "classroom_name":
                        classroom_name,

                    "subject_name":
                        subject_name,

                    "student_name":
                        student_name,

                    "admission_number":
                        getattr(
                            record.student,
                            "admission_number",
                            "N/A",
                        ),

                    "status":
                        record.status,

                    "remarks":
                        record.remarks or "",

                    "submission_status":
                        record.submission.status,

                    # ========================================
                    # MARKED BY
                    # ========================================

                    "marked_by_id":
                        marked_by_id,

                    "marked_by_name":
                        marked_by_name,

                    # ========================================
                    # CLASS TEACHER
                    # ========================================

                    "class_teacher_id":
                        class_teacher_id,

                    "class_teacher_name":
                        class_teacher_name,

                    "is_class_teacher":
                        is_class_teacher,
                }
            )

        return paginator.get_paginated_response(data)

# ============================================================
# ATTENDANCE REPORT — ADMIN / ACADEMIC COORDINATOR
#
# GET /api/attendance/report/
#
# Filters:
# ?classroom=<id>
# ?status=Present/Absent/Excused
# ?from_date=YYYY-MM-DD
# ?to_date=YYYY-MM-DD
# ============================================================

class AttendanceReportView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if request.user.role not in [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
        ]:

            return Response(
                {
                    "error": "Access denied."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        records = (
            Attendance.objects
            .filter(
                submission__status=
                    AttendanceSubmission.Status.FINAL
            )
            .select_related(
                "student",
                "submission",
                "submission__classroom",
            )
            .order_by(
                "-submission__date"
            )
        )

        classroom_id = request.query_params.get(
            "classroom"
        )

        status_param = request.query_params.get(
            "status"
        )

        from_date = request.query_params.get(
            "from_date"
        )

        to_date = request.query_params.get(
            "to_date"
        )

        if classroom_id:

            records = records.filter(
                submission__classroom_id=classroom_id
            )

        if status_param:

            records = records.filter(
                status=status_param
            )

        if from_date:

            records = records.filter(
                submission__date__gte=from_date
            )

        if to_date:

            records = records.filter(
                submission__date__lte=to_date
            )

        # BEFORE: 4 separate `.count()` queries re-running the same
        # filters, PLUS a full Python list comprehension over every
        # matching record with no pagination at all.
        #
        # AFTER: one `.aggregate()` for the summary numbers, and the
        # detail rows are paginated before we build the per-row dicts
        # — for a term's worth of attendance across a whole school
        # this is the difference between a handful of DB rows
        # touched per request and every attendance record ever
        # created.
        summary_counts = records.aggregate(
            total=Count("id"),
            present=Count("id", filter=Q(status=Attendance.Status.PRESENT)),
            absent=Count("id", filter=Q(status=Attendance.Status.ABSENT)),
            excused=Count("id", filter=Q(status=Attendance.Status.EXCUSED)),
        )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(records, request, view=self)

        data = [
            {
                "date":
                    record.submission.date,

                "student_name": (
                    f"{record.student.first_name} "
                    f"{record.student.last_name}"
                ).strip(),

                "admission_number":
                    record.student.admission_number,

                "class_name":
                    str(record.submission.classroom),

                "status":
                    record.status,

                "remarks":
                    record.remarks or "",
            }

            for record in page
        ]

        return Response(
            {
                "records":
                    data,

                "count": paginator.page.paginator.count,
                "total_pages": paginator.page.paginator.num_pages,
                "current_page": paginator.page.number,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),

                "summary": {

                    "total":
                        summary_counts["total"],

                    "present":
                        summary_counts["present"],

                    "absent":
                        summary_counts["absent"],

                    "excused":
                        summary_counts["excused"],
                },
            },

            status=status.HTTP_200_OK,
        ) 