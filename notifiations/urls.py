from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    MyNotificationsView,
    NotificationDetailView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadNotificationCountView,
)

router = DefaultRouter()
router.register(r"admin/notifications",NotificationViewSet,basename="admin-notifications")
urlpatterns = [
    # ===========================
    # Admin CRUD
    # ===========================
    path("", include(router.urls)),

    # ===========================
    # User Notifications
    # ===========================
    path("my/", MyNotificationsView.as_view(),name="my-notifications",),
    path("my/<int:pk>/",NotificationDetailView.as_view(),name="notification-detail",),
    path("my/<int:pk>/read/",MarkNotificationReadView.as_view(),name="mark-notification-read",),
    path("my/read-all/",MarkAllNotificationsReadView.as_view(),name="mark-all-notifications-read",), 
    path( "my/unread-count/", UnreadNotificationCountView.as_view(), name="unread-notification-count",),  
] 