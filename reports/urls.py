from django.urls import path

from .views import (
    ClassCapacityReport,
    DashboardStatisticsReport,
    FeeCollectionByTermReport,
    FeeSummaryReport,
    FinancialReport,
    FinancialReportExport,
    MonthlyFeeCollectionReport,
    NewAdmissionsReport,
    OutstandingBalancesReport,
    ParentChildrenReport,
    ParentContactReport,
    ParentFeeReport,
    ParentsWithOutstandingBalancesReport,
    ParentSummaryReport,
    SchoolSummaryReport,
    StudentStatusReport,
    StudentSummaryReport,
    StudentsByClassReport,
    StudentsByGenderReport,
    TeacherSummaryReport,
    TeachersByClassReport,
    TeachersBySubjectReport,
    TeacherWorkloadReport,
)

app_name = "reports"  # 🔑 Recommended: add namespace for reverse lookups

urlpatterns = [
    # =====================================================
    # FINANCIAL REPORTS
    # =====================================================
    path(
        "financial/generate/",
        FinancialReport.as_view(),
        name="financial-report",
    ),
    path(
        "financial/export/",
        FinancialReportExport.as_view(),
        name="financial-report-export",
    ),

    # =====================================================
    # SCHOOL REPORTS
    # =====================================================
    path(
        "school/class-capacity/",
        ClassCapacityReport.as_view(),
        name="class-capacity-report",
    ),
    path(
        "school/summary/",
        SchoolSummaryReport.as_view(),
        name="school-summary-report",
    ),

    # =====================================================
    # STUDENT REPORTS
    # =====================================================
    path(
        "students/status/",
        StudentStatusReport.as_view(),
        name="student-status-report",
    ),
    path(
        "students/summary/",
        StudentSummaryReport.as_view(),
        name="student-summary-report",
    ),
    path(
        "students/by-class/",
        StudentsByClassReport.as_view(),
        name="students-by-class-report",
    ),
    path(
        "students/by-gender/",
        StudentsByGenderReport.as_view(),
        name="students-by-gender-report",
    ),
    path(
        "students/new-admissions/",
        NewAdmissionsReport.as_view(),
        name="new-admissions-report",
    ),

    # =====================================================
    # FEE REPORTS
    # =====================================================
    path(
        "fees/summary/",
        FeeSummaryReport.as_view(),
        name="fee-summary-report",
    ),
    path(
        "fees/by-term/",
        FeeCollectionByTermReport.as_view(),
        name="fee-collection-by-term-report",
    ),
    path(
        "fees/monthly/",
        MonthlyFeeCollectionReport.as_view(),
        name="monthly-fee-collection-report",
    ),
    path(
        "fees/outstanding-balances/",
        OutstandingBalancesReport.as_view(),
        name="outstanding-balances-report",
    ),

    # =====================================================
    # PARENT REPORTS
    # =====================================================
    path(
        "parents/summary/",
        ParentSummaryReport.as_view(),
        name="parent-summary-report",
    ),
    path(
        "parents/contact/",
        ParentContactReport.as_view(),
        name="parent-contact-report",
    ),
    path(
        "parents/children/",
        ParentChildrenReport.as_view(),
        name="parent-children-report",
    ),
    path(
        "parents/fees/",
        ParentFeeReport.as_view(),
        name="parent-fee-report",
    ),
    path(
        "parents/with-outstanding-balances/",
        ParentsWithOutstandingBalancesReport.as_view(),
        name="parents-with-outstanding-balances-report",
    ),

    # =====================================================
    # TEACHER REPORTS
    # =====================================================
    path(
        "teachers/summary/",
        TeacherSummaryReport.as_view(),
        name="teacher-summary-report",
    ),
    path(
        "teachers/workload/",
        TeacherWorkloadReport.as_view(),
        name="teacher-workload-report",
    ),
    path(
        "teachers/by-class/",
        TeachersByClassReport.as_view(),
        name="teachers-by-class-report",
    ),
    path(
        "teachers/by-subject/",
        TeachersBySubjectReport.as_view(),
        name="teachers-by-subject-report",
    ),

    # =====================================================
    # DASHBOARD
    # =====================================================
    path(
        "dashboard/statistics/",
        DashboardStatisticsReport.as_view(),
        name="dashboard-statistics-report",
    ),
]