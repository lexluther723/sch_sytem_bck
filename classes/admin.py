from django.contrib import admin
from .models import ClassRoom

# Register your models here.
@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = (
        "grade",
        "stream",
        "capacity",
        "class_teacher",
        "created_at",
    )

    list_filter = (
        "grade",
        "stream",
    )

    search_fields = (
        "grade",
        "stream",
        "class_teacher__user__first_name",
        "class_teacher__user__last_name",
    )

    ordering = (
        "grade",
        "stream",
    )