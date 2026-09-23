from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    CustomUser,
    ParentProfile,
    TeacherProfile,
    AccountantProfile,
    AcademicCoordinatorProfile,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "role",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )

    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "profile_picture",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "occupation",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
    )

    ordering = ("user__first_name",)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "employee_number",
        "qualification",
        "employment_date",
    )

    search_fields = (
        "employee_number",
        "user__username",
        "user__first_name",
        "user__last_name",
    )

    ordering = ("employee_number",)


@admin.register(AccountantProfile)
class AccountantProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "employee_number",
    )

    search_fields = (
        "employee_number",
        "user__username",
    )

    ordering = ("employee_number",)


@admin.register(AcademicCoordinatorProfile)
class AcademicCoordinatorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "employee_number",
    )

    search_fields = (
        "employee_number",
        "user__username",
    )

    ordering = ("employee_number",) 