from django.db.models import Q

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response

# Preserved your exact import spelling
from notifiations.models import Notification
from accounts.models import CustomUser

from .models import Announcement
from .serializers import AnnouncementSerializer
from .permissions import IsSuperAdminOrAcademicCoordinator


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    queryset = Announcement.objects.all()
    ordering = ["-created_at"]
    pagination_class = PageNumberPagination

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "title",
        "message",
    ]

    ordering_fields = [
        "created_at",
        "priority",
    ]

    # =====================================================
    # QUERYSET
    # =====================================================

    def get_queryset(self):
        user = self.request.user

        # -------------------------------------------------
        # PARENT
        # -------------------------------------------------

        if user.role == CustomUser.Role.PARENT:
            return (
                super()
                .get_queryset()
                .filter(
                    is_active=True
                )
                .filter(
                    Q(
                        target=Announcement.Target.ALL_USERS
                    )
                    |
                    Q(
                        target=Announcement.Target.PARENTS
                    )
                    |
                    Q(
                        recipient=user
                    )
                )
                .distinct()
            )

        # -------------------------------------------------
        # TEACHER
        # -------------------------------------------------

        elif user.role == CustomUser.Role.TEACHER:
            return (
                super()
                .get_queryset()
                .filter(
                    is_active=True
                )
                .filter(
                    Q(
                        target=Announcement.Target.ALL_USERS
                    )
                    |
                    Q(
                        target=Announcement.Target.STAFF
                    )
                    |
                    Q(
                        target=Announcement.Target.TEACHERS
                    )
                    |
                    Q(
                        recipient=user
                    )
                )
                .distinct()
            )

        # -------------------------------------------------
        # ADMIN / ACADEMIC COORDINATOR / ACCOUNTANT
        # -------------------------------------------------
        #
        # These users manage announcements.
        # They need the complete queryset so that retrieve,
        # update and delete do not incorrectly return 404
        # for announcements targeted at another audience.

        return super().get_queryset()

    # =====================================================
    # PERMISSIONS
    # =====================================================

    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            permission_classes = [
                IsSuperAdminOrAcademicCoordinator
            ]
        else:
            permission_classes = [
                IsAuthenticated
            ]

        return [
            permission()
            for permission in permission_classes
        ]

    # =====================================================
    # CREATE ANNOUNCEMENT
    # =====================================================

    def perform_create(self, serializer):

        announcement = serializer.save(
            created_by=self.request.user
        )

        # -------------------------------------------------
        # SPECIFIC RECIPIENT
        # -------------------------------------------------

        if announcement.recipient is not None:

            Notification.objects.create(
                recipient=announcement.recipient,
                triggered_by=self.request.user,
                notification_type=(
                    Notification.NotificationType.ANNOUNCEMENT
                ),
                title=announcement.title,
                message=announcement.message,
            )

            return

        # -------------------------------------------------
        # BROADCAST TO TARGET AUDIENCE
        # -------------------------------------------------

        recipients = self._resolve_recipients(
            announcement.target
        )

        if recipients.exists():

            notifications = [
                Notification(
                    recipient=recipient,
                    triggered_by=self.request.user,
                    notification_type=(
                        Notification.NotificationType.ANNOUNCEMENT
                    ),
                    title=announcement.title,
                    message=announcement.message,
                )
                for recipient in recipients
            ]

            Notification.objects.bulk_create(
                notifications
            )

    # =====================================================
    # RESOLVE RECIPIENTS
    # =====================================================

    def _resolve_recipients(self, target):

        if target == Announcement.Target.ALL_USERS:

            return CustomUser.objects.filter(
                is_active=True
            )

        elif target == Announcement.Target.PARENTS:

            return CustomUser.objects.filter(
                role=CustomUser.Role.PARENT,
                is_active=True,
            )

        elif target == Announcement.Target.TEACHERS:

            return CustomUser.objects.filter(
                role=CustomUser.Role.TEACHER,
                is_active=True,
            )

        elif target == Announcement.Target.STAFF:

            return CustomUser.objects.filter(
                role__in=[
                    CustomUser.Role.SUPER_ADMIN,
                    CustomUser.Role.ACADEMIC_COORDINATOR,
                    CustomUser.Role.ACCOUNTANT,
                    CustomUser.Role.TEACHER,
                ],
                is_active=True,
            )

        return CustomUser.objects.none()

    # =====================================================
    # RESEND ANNOUNCEMENT
    # =====================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="resend",
    )
    def resend(self, request, pk=None):

        try:

            announcement = self.get_object()

            # -------------------------------------------------
            # SPECIFIC RECIPIENT
            # -------------------------------------------------

            if announcement.recipient is not None:

                Notification.objects.create(
                    recipient=announcement.recipient,
                    triggered_by=request.user,
                    notification_type=(
                        Notification.NotificationType.ANNOUNCEMENT
                    ),
                    title=announcement.title,
                    message=announcement.message,
                )

                return Response(
                    {
                        "detail": (
                            "Resent successfully! "
                            "Sent to 1 recipient."
                        )
                    },
                    status=status.HTTP_200_OK,
                )

            # -------------------------------------------------
            # TARGET AUDIENCE
            # -------------------------------------------------

            recipients = self._resolve_recipients(
                announcement.target
            )

            created_count = 0

            if recipients.exists():

                notifications = [
                    Notification(
                        recipient=recipient,
                        triggered_by=request.user,
                        notification_type=(
                            Notification.NotificationType.ANNOUNCEMENT
                        ),
                        title=announcement.title,
                        message=announcement.message,
                    )
                    for recipient in recipients
                ]

                Notification.objects.bulk_create(
                    notifications
                )

                created_count = len(notifications)

            return Response(
                {
                    "detail": (
                        "Resent successfully! "
                        f"Sent to {created_count} recipients."
                    )
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:

            print(
                "RESEND ERROR:",
                str(e)
            )

            return Response(
                {
                    "detail": (
                        f"Failed to resend: {str(e)}"
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )