from rest_framework import serializers

from .models import Timetable


class TimetableSerializer(serializers.ModelSerializer):

    # =====================================================
    # DISPLAY FIELDS
    # =====================================================

    teacher_name = serializers.CharField(
        source="assignment.teacher.user.get_full_name",
        read_only=True,
    )

    subject_name = serializers.CharField(
        source="assignment.subject.name",
        read_only=True,
    )

    classroom_name = serializers.SerializerMethodField()

    # =====================================================
    # IDS
    # =====================================================

    teacher_id = serializers.IntegerField(
        source="assignment.teacher.id",
        read_only=True,
    )

    subject_id = serializers.IntegerField(
        source="assignment.subject.id",
        read_only=True,
    )

    classroom_id = serializers.IntegerField(
        source="assignment.classroom.id",
        read_only=True,
    )

    # =====================================================
    # CLASS DETAILS
    # =====================================================

    grade = serializers.CharField(
        source="assignment.classroom.grade",
        read_only=True,
    )

    stream = serializers.CharField(
        source="assignment.classroom.stream",
        read_only=True,
    )

    # =====================================================
    # DAY
    # =====================================================

    day_display = serializers.CharField(
        source="get_day_display",
        read_only=True,
    )

    # =====================================================
    # CLASS NAME
    # =====================================================

    def get_classroom_name(self, obj):
        classroom = obj.assignment.classroom

        if hasattr(classroom, "name") and classroom.name:
            return classroom.name

        grade = getattr(classroom, "grade", "")
        stream = getattr(classroom, "stream", "")

        name = f"{grade} {stream}".strip()

        return name or str(classroom)

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate(self, attrs):
        """
        Ensure that the timetable end time is after
        the start time.

        This validation is done here because Django's
        model clean() method is not automatically called
        by DRF serializers.
        """

        start_time = attrs.get(
            "start_time",
            getattr(self.instance, "start_time", None),
        )

        end_time = attrs.get(
            "end_time",
            getattr(self.instance, "end_time", None),
        )

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                "end_time": "End time must be later than start time."
            })

        return attrs

    # =====================================================
    # META
    # =====================================================

    class Meta:
        model = Timetable

        fields = [
            "id",

            "academic_year",
            "term",

            "day",
            "day_display",

            "start_time",
            "end_time",

            "assignment",

            "teacher_id",
            "teacher_name",

            "subject_id",
            "subject_name",

            "classroom_id",
            "classroom_name",

            "grade",
            "stream",

            "is_active",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",

            "teacher_id",
            "teacher_name",

            "subject_id",
            "subject_name",

            "classroom_id",
            "classroom_name",

            "grade",
            "stream",
        ] 