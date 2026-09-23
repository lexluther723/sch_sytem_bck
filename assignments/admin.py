# from django.contrib import admin
# from .models import TeacherAssignment, TeacherProfile


# @admin.register(TeacherAssignment)
# class TeacherAssignmentAdmin(admin.ModelAdmin):
#     list_display = (
#         "teacher",
#         "classroom",
#         "subject",
#         "academic_year",
#         "term",
#         "is_class_teacher",
#         "is_active",
#     )

#     list_filter = (
#         "academic_year",
#         "term",
#         "is_class_teacher",
#         "is_active",
#     )

#     search_fields = (
#         "teacher__user__first_name",
#         "teacher__user__last_name",
#         "subject__name",
#         "classroom__grade",
#     )

#     ordering = (
#         "-academic_year",
#         "term",
#     )


# @admin.register(TeacherProfile)
# class TeacherProfileAdmin(admin.ModelAdmin):
#     list_display = (
#         "employee_number",
#         "first_name",
#         "last_name",
#         "phone_number",
#         "employment_status",
#     )

#     list_filter = (
#         "employment_status",
#         "gender",
#     )

#     search_fields = (
#         "employee_number",
#         "first_name",
#         "last_name",
#         "national_id",
#     )