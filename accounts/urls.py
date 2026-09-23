from django.urls import include, path

from .views import (
    ChangePassword,
    DeleteUser,
    Login,
    Logout,
    ParentList,
    Register,
    ResetPassword,
    RestoreUser,
    StudentProfileView,
    UpdateUser,
    UserDetail,
    test,
    UserList,

    AcademicCoordinatorProfileView,
    TeacherProfileView,
    AccountantProfileView,
    ParentProfileView,

    # NEW
    TeacherProfilesListView,
)


urlpatterns = [

    # =====================================================
    # AUTH
    # =====================================================

    path(
        "login/",
        Login,
        name="login",
    ),

    path(
        "logout/",
        Logout,
        name="logout",
    ),

    path(
        "test/",
        test,
        name="test",
    ),

    path(
        "password/reset/",
        include(
            "django_rest_passwordreset.urls",
            namespace="password_reset",
        ),
    ),


    # =====================================================
    # REGISTRATION
    # =====================================================

    path(
        "register/",
        Register,
        name="register",
    ),


    # =====================================================
    # USER MANAGEMENT
    # =====================================================

    path(
        "parents/",
        ParentList,
        name="parent-list",
    ),

    path(
        "users/",
        UserList,
        name="user-list",
    ),

    path(
        "users/<int:id>/",
        UserDetail,
        name="user-detail",
    ),

    path(
        "users/<int:id>/update/",
        UpdateUser,
        name="update-user",
    ),

    path(
        "users/<int:id>/delete/",
        DeleteUser,
        name="delete-user",
    ),

    path(
        "users/<int:id>/restore/",
        RestoreUser,
        name="restore-user",
    ),


    # =====================================================
    # PASSWORD
    # =====================================================

    path(
        "change-password/",
        ChangePassword,
        name="change-password",
    ),

    path(
        "reset-password/<int:id>/",
        ResetPassword,
        name="reset-password",
    ),


    # =====================================================
    # CURRENT USER PROFILE ENDPOINTS
    #
    # These are for the logged-in user's own profile.
    # =====================================================

    path(
        "coordinator-profile/",
        AcademicCoordinatorProfileView.as_view(),
        name="coordinator-profile",
    ),

    path(
        "teacher-profile/",
        TeacherProfileView.as_view(),
        name="teacher-profile",
    ),

    path(
        "accountant-profile/",
        AccountantProfileView.as_view(),
        name="accountant-profile",
    ),

    path(
        "parent-profile/",
        ParentProfileView.as_view(),
        name="parent-profile",
    ),

    path(
        "student-profilesmoan/",
        StudentProfileView.as_view(),
        name="student-profile",
    ),
    path(
        "student-profile/<int:pk>/",
        StudentProfileView.as_view(),
        name="student-profile-detail",
    ),


    # =====================================================
    # ALL TEACHER PROFILES
    #
    # Used by Academic Coordinator / Super Admin.
    #
    # GET:
    #     /api/accounts/teacher-profiles/
    #
    # This returns ALL registered TeacherProfile records.
    # =====================================================

    path(
        "teacher-profiles/",
        TeacherProfilesListView.as_view(),
        name="teacher-profiles-list",
    ),
]