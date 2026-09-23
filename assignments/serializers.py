from rest_framework import serializers
from .models import TeacherAssignment
from accounts.models import TeacherProfile


# =====================================================
# TEACHER ASSIGNMENT SERIALIZER
# =====================================================

class TeacherAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    teacher_first_name = serializers.SerializerMethodField()
    teacher_last_name = serializers.SerializerMethodField()
    staff_number = serializers.SerializerMethodField()

    classroom_name = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    stream = serializers.SerializerMethodField()

    subject_name = serializers.CharField(
        source="subject.name",
        read_only=True
    )

    class Meta:
        model = TeacherAssignment

        fields = [
            "id",

            # Teacher
            "teacher",
            "teacher_name",
            "teacher_first_name",
            "teacher_last_name",
            "staff_number",

            # Classroom
            "classroom",
            "classroom_name",
            "grade",
            "stream",

            # Subject
            "subject",
            "subject_name",

            # Assignment information
            "academic_year",
            "term",
            "is_class_teacher",
            "is_active",

            "assigned_date",
            "end_date",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "assigned_date",
            "created_at",
            "updated_at",
        ]

    # =================================================
    # TEACHER
    # =================================================

    def get_teacher_name(self, obj):
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.get_full_name() or obj.teacher.user.username

        return "Unknown Teacher"

    def get_teacher_first_name(self, obj):
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.first_name

        return ""

    def get_teacher_last_name(self, obj):
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.last_name

        return ""

    def get_staff_number(self, obj):
        if not obj.teacher:
            return "—"

        return (
            getattr(obj.teacher, "employee_number", None)
            or getattr(obj.teacher, "staff_number", None)
            or "—"
        )

    # =================================================
    # CLASSROOM
    # =================================================

    def get_classroom_name(self, obj):
        if not obj.classroom:
            return "—"

        return str(obj.classroom)

    def get_grade(self, obj):
        return getattr(obj.classroom, "grade", "") or ""

    def get_stream(self, obj):
        return getattr(obj.classroom, "stream", "") or ""

    # =================================================
    # VALIDATION
    # =================================================

    def validate(self, attrs):
        teacher = attrs.get(
            "teacher",
            self.instance.teacher if self.instance else None
        )

        classroom = attrs.get(
            "classroom",
            self.instance.classroom if self.instance else None
        )

        subject = attrs.get(
            "subject",
            self.instance.subject if self.instance else None
        )

        academic_year = attrs.get(
            "academic_year",
            self.instance.academic_year if self.instance else None
        )

        term = attrs.get(
            "term",
            self.instance.term if self.instance else None
        )

        is_class_teacher = attrs.get(
            "is_class_teacher",
            self.instance.is_class_teacher if self.instance else False
        )

        # =================================================
        # CLASS TEACHER VALIDATION
        # =================================================

        if is_class_teacher:

            # A classroom can have only ONE active class teacher
            classroom_queryset = TeacherAssignment.objects.filter(
                classroom=classroom,
                term=term,
                academic_year=academic_year,
                is_class_teacher=True,
                is_active=True,
            )

            # A teacher can only be class teacher for ONE classroom
            teacher_queryset = TeacherAssignment.objects.filter(
                teacher=teacher,
                term=term,
                academic_year=academic_year,
                is_class_teacher=True,
                is_active=True,
            )

            if self.instance:
                classroom_queryset = classroom_queryset.exclude(
                    pk=self.instance.pk
                )

                teacher_queryset = teacher_queryset.exclude(
                    pk=self.instance.pk
                )

            if classroom_queryset.exists():
                raise serializers.ValidationError({
                    "classroom":
                        "This classroom already has an active class teacher."
                })

            if teacher_queryset.exists():
                raise serializers.ValidationError({
                    "teacher":
                        "This teacher is already a class teacher for another classroom."
                })

        # =================================================
        # SAME TEACHER / CLASS / SUBJECT DUPLICATE
        # =================================================

        duplicate_queryset = TeacherAssignment.objects.filter(
            teacher=teacher,
            classroom=classroom,
            subject=subject,
            academic_year=academic_year,
            term=term,
        )

        if self.instance:
            duplicate_queryset = duplicate_queryset.exclude(
                pk=self.instance.pk
            )

        if duplicate_queryset.exists():
            raise serializers.ValidationError({
                "non_field_errors":
                    "This teacher is already assigned to this subject and classroom for this academic year and term."
            })

        return attrs


# =====================================================
# TEACHER PROFILE SERIALIZER
# =====================================================

class TeacherProfileSerializer(serializers.ModelSerializer):

    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = "__all__"

    def get_teacher_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username

        return "Unknown Teacher"