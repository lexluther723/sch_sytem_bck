from rest_framework import serializers
from .models import ParentProfile
from students.models import Student


class ParentSerializer(serializers.ModelSerializer):

    full_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(
        source="user.phone_number",
        read_only=True
    )

    children_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = ParentProfile

        fields = [
            "id",
            "user",
            "full_name",
            "phone_number",
            "occupation",
            "address",
            "children_count",
            "children",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "full_name",
            "phone_number",
            "children_count",
            "children",
            "created_at",
            "updated_at",
        ]

    # =================================================
    # Parent full name
    # =================================================

    def get_full_name(self, obj):

        return obj.user.get_full_name()

    # =================================================
    # Number of children
    # =================================================

    def get_children_count(self, obj):

        return obj.children.count()

    # =================================================
    # Parent's children
    # =================================================

    def get_children(self, obj):

        children = obj.children.select_related(
            "classroom"
        ).all()

        return [
            {
                "id": student.id,
                "admission_number": student.admission_number,
                "assessment_number": student.assessment_number,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "gender": student.gender,
                "date_of_birth": student.date_of_birth,
                "classroom": student.classroom.id
                if student.classroom else None,
                "classroom_name": str(student.classroom)
                if student.classroom else None,
                "status": student.status,
                "photo": student.photo.url
                if student.photo else None,
            }
            for student in children
        ]