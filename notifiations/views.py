from django.utils import timezone

from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser

from .models import Notification
from .permissions import (
    IsNotificationRecipient,
    IsSuperAdmin,
)
from .serializers import NotificationSerializer
from .services import (
    create_notification,
    create_bulk_notifications,
)


# ===========================
# User Views
# ===========================

class MyNotificationsView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Notification.objects.select_related(
                "recipient",
                "triggered_by",
            )
            .filter(recipient=self.request.user)
        )


class NotificationDetailView(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [
        IsAuthenticated,
        IsNotificationRecipient,
    ]

    def get_queryset(self):
        return (
            Notification.objects.select_related(
                "recipient",
                "triggered_by",
            )
            .filter(recipient=self.request.user)
        )


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk,
                recipient=request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.is_read = True

        # Only if read_at exists in your model
        if hasattr(notification, "read_at"):
            notification.read_at = timezone.now()
            notification.save(
                update_fields=["is_read", "read_at"]
            )
        else:
            notification.save(update_fields=["is_read"])

        return Response(
            {
                "message": "Notification marked as read."
            },
            status=status.HTTP_200_OK,
        )


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        )

        if hasattr(Notification, "read_at"):
            notifications.update(
                is_read=True,
                read_at=timezone.now(),
            )
        else:
            notifications.update(
                is_read=True,
            )

        return Response(
            {
                "message": "All notifications marked as read."
            },
            status=status.HTTP_200_OK,
        )


class UnreadNotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()

        return Response(
            {
                "unread_count": count
            },
            status=status.HTTP_200_OK,
        )


# ===========================
# Super Admin Views
# ===========================

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.select_related(
        "recipient",
        "triggered_by",
    )
    serializer_class = NotificationSerializer
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        serializer.save(
            triggered_by=self.request.user
        )

    def create(self, request, *args, **kwargs):
        send_to = request.data.get("send_to")

        title = request.data.get("title")
        message = request.data.get("message")
        notification_type = request.data.get(
            "notification_type"
        )

        if send_to == "all":
            users = CustomUser.objects.all()

            create_bulk_notifications(
                recipients=users,
                title=title,
                message=message,
                notification_type=notification_type,
                triggered_by=request.user,
            )

            return Response(
                {
                    "message": "Notification sent to all users."
                },
                status=status.HTTP_201_CREATED,
            )

        recipient_id = request.data.get("recipient")

        if recipient_id:
            try:
                recipient = CustomUser.objects.get(
                    pk=recipient_id
                )
            except CustomUser.DoesNotExist:
                return Response(
                    {
                        "error": "Recipient not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            notification = create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                triggered_by=request.user,
            )

            serializer = self.get_serializer(notification)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "error": "Recipient is required."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )