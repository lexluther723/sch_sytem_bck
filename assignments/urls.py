from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TeacherProfileListView,
    TeacherAssignmentListView,
    TeacherAssignmentCreateView,
    TeacherAssignmentDetailView,
    TeacherAssignmentUpdateView,
    TeacherAssignmentDeleteView,
    TeacherProfileViewSet,
)

router = DefaultRouter()
router.register(r"my-profile", TeacherProfileViewSet, basename="my-profile")

urlpatterns = [
    path("teachers/", TeacherProfileListView.as_view(), name="teacher-list"),  # ✅ Dropdown source
    path("", TeacherAssignmentListView.as_view(), name="assignment-list"),
    path("create/", TeacherAssignmentCreateView.as_view(), name="assignment-create"),
    path("<int:pk>/", TeacherAssignmentDetailView.as_view(), name="assignment-detail"),
    path("update/<int:pk>/", TeacherAssignmentUpdateView.as_view(), name="assignment-update"),
    path("delete/<int:pk>/", TeacherAssignmentDeleteView.as_view(), name="assignment-delete"),
    path("", include(router.urls)),
]