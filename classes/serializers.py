from rest_framework import serializers
from .models import ClassRoom


class ClassRoomSerializer(serializers.ModelSerializer):
    class_teacher_name = serializers.SerializerMethodField()

    # ==================================================
    # total_students
    #
    # BUG THIS FIXES
    # --------------
    # `ClassRoom.total_students` is a denormalised counter column that
    # was maintained by three signal receivers in students/Signals.py.
    # Nothing ever imported that module (students/apps.py has no
    # ready(), and the file is capital-S "Signals.py"), so the
    # receivers never connected and EVERY classroom reported 0
    # students, forever - while this serializer happily shipped that
    # 0 to the frontend.
    #
    # Rather than reconnect a counter that can drift out of sync (and
    # that fired an extra full_clean() query per student on every
    # save), the value is now computed. Views annotate the queryset
    # with `student_count`; this field prefers that annotation and
    # falls back to a direct count for single-object reads.
    #
    # The JSON key and type are unchanged, so the frontend sees no
    # difference except that the number is now correct.
    # ==================================================
    total_students = serializers.SerializerMethodField()

    def get_total_students(self, obj):
        annotated = getattr(obj, "student_count", None)
        if annotated is not None:
            return annotated
        return obj.students.count()

    class Meta:
        model = ClassRoom
        fields = [
            "id",
            "grade",
            "stream",
            "capacity",
            "total_students",
            "class_teacher",
            "class_teacher_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "total_students",
            "created_at",
            "class_teacher_name",
        ]

    def get_class_teacher_name(self, obj):
        if obj.class_teacher:
            return obj.class_teacher.user.get_full_name()
        return None

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Capacity must be greater than zero."
            )

        if value > 100:
            raise serializers.ValidationError(
                "Capacity cannot exceed 100 students."
            )

        return value

    def validate_class_teacher(self, teacher):
        if teacher is None:
            return teacher

        queryset = ClassRoom.objects.filter(
            class_teacher=teacher
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "This teacher is already assigned as a class teacher."
            )

        return teacher

    def validate(self, attrs):
        grade = attrs.get(
            "grade",
            self.instance.grade if self.instance else None
        )

        stream = attrs.get(
            "stream",
            self.instance.stream if self.instance else None
        )

        if grade and stream:
            queryset = ClassRoom.objects.filter(
                grade=grade,
                stream=stream,
            )

            if self.instance:
                queryset = queryset.exclude(
                    pk=self.instance.pk
                )

            if queryset.exists():
                raise serializers.ValidationError({
                    "stream": "This grade and stream already exists."
                })

        return attrs