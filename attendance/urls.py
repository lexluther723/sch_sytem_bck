from django.urls import path

from .views import (
    AttendanceSubmissionCreateView,
    MarkAttendanceView,
    SubmitAttendanceView,
    AttendanceDetailView,
    StudentAttendanceHistoryView,
    TeacherAttendanceHistoryView,
    AttendanceReportView,
)


urlpatterns = [
    # ============================================================
    # CREATE / LOAD ATTENDANCE SUBMISSION
    # ============================================================

    path(
        "submissions/create/",
        AttendanceSubmissionCreateView.as_view(),
        name="attendance-submission-create",
    ),

    # ============================================================
    # MARK ATTENDANCE
    #
    # GET  -> Load students
    # POST -> Save + finalize attendance
    # ============================================================

    path(
        "mark/",
        MarkAttendanceView.as_view(),
        name="mark-attendance",
    ),

    # ============================================================
    # SUBMIT ATTENDANCE
    #
    # Kept for backward compatibility.
    # Attendance is already finalized by mark/.
    # ============================================================

    path(
        "submit/",
        SubmitAttendanceView.as_view(),
        name="submit-attendance",
    ),

    # ============================================================
    # ATTENDANCE DETAIL
    # Admin / Academic Coordinator
    # ============================================================

    path(
        "detail/<int:submission_id>/",
        AttendanceDetailView.as_view(),
        name="attendance-detail",
    ),

    # ============================================================
    # STUDENT ATTENDANCE HISTORY
    # ============================================================

    path(
        "student/<int:student_id>/history/",
        StudentAttendanceHistoryView.as_view(),
        name="student-attendance-history",
    ),

    # ============================================================
    # TEACHER ATTENDANCE HISTORY
    # ============================================================

    path(
        "teacher/history/",
        TeacherAttendanceHistoryView.as_view(),
        name="teacher-attendance-history",
    ),

    # ============================================================
    # ADMIN ATTENDANCE REPORT
    # ============================================================

    path(
        "report/",
        AttendanceReportView.as_view(),
        name="attendance-report",
    ),
]