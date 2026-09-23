from django.urls import path

from .views import (
    ClassRoomListView,
    ClassRoomDetailView,
    ClassRoomCreateView,
    ClassRoomUpdateView,
    ClassRoomDeleteView,
)


urlpatterns = [
    # GET
    path(
        "",
        ClassRoomListView.as_view(),
        name="classroom-list",
    ),

    # GET single class
    path(
        "<int:pk>/",
        ClassRoomDetailView.as_view(),
        name="classroom-detail",
    ),

    # POST
    path(
        "create/",
        ClassRoomCreateView.as_view(),
        name="classroom-create",
    ),

    # PUT / PATCH
    path(
        "update/<int:pk>/",
        ClassRoomUpdateView.as_view(),
        name="classroom-update",
    ),

    # DELETE
    path(
        "delete/<int:pk>/",
        ClassRoomDeleteView.as_view(),
        name="classroom-delete",
    ),
]