from rest_framework import serializers

from .models import Exam


# =====================================================
# Exam Serializer
# =====================================================
class ExamSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(
        source="classroom.__str__",
        read_only=True
    )

    subject_name = serializers.CharField(
        source="subject.name",
        read_only=True
    )

    class Meta:
        model = Exam
        fields = [
            "id",
            "classroom",
            "classroom_name",
            "subject",
            "subject_name",
            "exam_type",
            "term",
            "academic_year",
            "exam_date",
            "total_marks",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
        ]