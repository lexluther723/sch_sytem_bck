from django.urls import path
from .views import (
    DashboardAPIView,
    DashboardFeeSummaryAPIView,
    ExamPerformanceDashboardAPIView,
    ParentReportCardsAPIView,
    RecentAdmissionsAPIView,
    RecentFeePaymentsAPIView,
    TodayAttendanceSummaryAPIView,
    TopOutstandingStudentsAPIView,
    TopPerformingClassesAPIView,
    UpcomingNotificationsAPIView,
    ParentDashboardAPIView,
    ParentChildrenAPIView,
    ParentChildDetailsAPIView,
    TeacherDashboardAPIView,
    TeacherStudentsAPIView,
    TeacherStudentDetailsAPIView,
    TeacherStudentResultsAPIView,
    TeacherUpdateStudentResultAPIView,
    TeacherAssessmentListAPIView,
    TeacherAssessmentDetailsAPIView,
    TeacherSaveAssessmentMarksAPIView,
)

urlpatterns = [
    path("", DashboardAPIView.as_view(), name="dashboard"),
    path("top-students/", TopOutstandingStudentsAPIView.as_view(), name="top-students"),
    path("top-classes/", TopPerformingClassesAPIView.as_view(), name="top-performing-classes"),
    path("recent-payments/", RecentFeePaymentsAPIView.as_view(), name="recent-fee-payments"),
    path("recent-admissions/", RecentAdmissionsAPIView.as_view(), name="recent-admissions"),
    path("attendance/today/", TodayAttendanceSummaryAPIView.as_view(), name="today-attendance-summary"),
    path("fees/summary/", DashboardFeeSummaryAPIView.as_view(), name="dashboard-fee-summary"),
    path("exam-performance/", ExamPerformanceDashboardAPIView.as_view(), name="exam-performance-dashboard"),
    path("notifications/", UpcomingNotificationsAPIView.as_view(), name="dashboard-notifications"),

    # Parent
    path("parent/", ParentDashboardAPIView.as_view(), name="parent-dashboard"),
    path("parent/children/", ParentChildrenAPIView.as_view(), name="parent-children"),
    path("parent/children/<int:id>/", ParentChildDetailsAPIView.as_view(), name="parent-child-details"),

    # Teacher
    path("teacher/", TeacherDashboardAPIView.as_view(), name="teacher-dashboard"),
    path("teacher/students/", TeacherStudentsAPIView.as_view(), name="teacher-students"),
    path("teacher/students/<int:pk>/", TeacherStudentDetailsAPIView.as_view(), name="teacher-student-details"),
    path("teacher/students/<int:pk>/results/", TeacherStudentResultsAPIView.as_view(), name="teacher-student-results"),
    path("teacher/results/<int:pk>/update/", TeacherUpdateStudentResultAPIView.as_view(), name="teacher-update-result"),
    path("teacher/assessments/", TeacherAssessmentListAPIView.as_view(), name="teacher-assessment-list"),
    path("teacher/assessments/<int:pk>/", TeacherAssessmentDetailsAPIView.as_view(), name="teacher-assessment-details"),
    path("teacher/assessments/<int:pk>/save-marks/", TeacherSaveAssessmentMarksAPIView.as_view(), name="teacher-save-marks"),
    path(
        "parent/report-cards/",
        ParentReportCardsAPIView.as_view(),
        name="parent-report-cards"
    ),
]
