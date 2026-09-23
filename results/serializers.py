from rest_framework import serializers

from .models import (
    GradeScale,
    LearningOutcome,
    AssessmentType,
    Assessment,
    ResultSubmission,
    Result,
    StudentResult,
    StudentTermResult,
    ReportComment,
    AssessmentRubric,
)


# ============================================================
# GRADE SCALE
# ============================================================

class GradeScaleSerializer(serializers.ModelSerializer):

    class Meta:
        model = GradeScale
        fields = "__all__"

    def validate(self, attrs):
        minimum = attrs.get("minimum_score")
        maximum = attrs.get("maximum_score")

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                raise serializers.ValidationError(
                    {
                        "maximum_score":
                            "Maximum score cannot be lower than minimum score."
                    }
                )

        return attrs


# ============================================================
# LEARNING OUTCOME
# ============================================================

class LearningOutcomeSerializer(serializers.ModelSerializer):

    subject_name = serializers.CharField(
        source="subject.name",
        read_only=True
    )

    classroom_name = serializers.CharField(
        source="classroom.name",
        read_only=True
    )

    class Meta:
        model = LearningOutcome
        fields = "__all__"

    def validate_maximum_marks(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Maximum marks must be greater than zero."
            )

        return value

# ============================================================
# ASSESSMENT TYPE
# ============================================================

class AssessmentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssessmentType
        fields = "__all__"

    def validate_percentage(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Percentage must be greater than zero."
            )

        if value > 100:
            raise serializers.ValidationError(
                "Percentage cannot exceed 100."
            )

        return value


# ============================================================
# ASSESSMENT
# ============================================================

class AssessmentSerializer(serializers.ModelSerializer):

    subject_name = serializers.CharField(
        source="subject.name",
        read_only=True
    )

    classroom_name = serializers.CharField(
        source="classroom.name",
        read_only=True
    )

    created_by_name = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = Assessment
        fields = "__all__"

        read_only_fields = (
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_created_by_name(self, obj):

        if not obj.created_by:
            return None

        return obj.created_by.get_full_name() or obj.created_by.username

    def validate_total_marks(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Total marks must be greater than zero."
            )

        return value

    def validate(self, attrs):

        subject = attrs.get("subject")
        classroom = attrs.get("classroom")
        term = attrs.get("term")
        academic_year = attrs.get("academic_year")

        if not subject:
            raise serializers.ValidationError(
                {
                    "subject": "Subject is required."
                }
            )

        if not classroom:
            raise serializers.ValidationError(
                {
                    "classroom": "Classroom is required."
                }
            )

        if not term:
            raise serializers.ValidationError(
                {
                    "term": "Term is required."
                }
            )

        if not academic_year:
            raise serializers.ValidationError(
                {
                    "academic_year": "Academic year is required."
                }
            )

        return attrs


# ============================================================
# RESULT SUBMISSION
# ============================================================

class ResultSubmissionSerializer(serializers.ModelSerializer):

    assessment_name = serializers.SerializerMethodField(
        read_only=True
    )

    submitted_by_name = serializers.SerializerMethodField(
        read_only=True
    )

    approved_by_name = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = ResultSubmission
        fields = "__all__"

        read_only_fields = (
            "submitted_by",
            "submitted_at",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        )

    def get_assessment_name(self, obj):

        if not obj.assessment:
            return None

        return str(obj.assessment)

    def get_submitted_by_name(self, obj):

        if not obj.submitted_by:
            return None

        return (
            obj.submitted_by.get_full_name()
            or obj.submitted_by.username
        )

    def get_approved_by_name(self, obj):

        if not obj.approved_by:
            return None

        return (
            obj.approved_by.get_full_name()
            or obj.approved_by.username
        )


# ============================================================
# RESULT
# ============================================================

class ResultSerializer(serializers.ModelSerializer):

    student_name = serializers.SerializerMethodField(
        read_only=True
    )

    grade_name = serializers.CharField(
        source="grade.level",
        read_only=True
    )

    grade_description = serializers.CharField(
        source="grade.description",
        read_only=True
    )

    assessment_name = serializers.SerializerMethodField(
        read_only=True
    )

    subject_name = serializers.SerializerMethodField(
        read_only=True
    )

    classroom_name = serializers.SerializerMethodField(
        read_only=True
    )

    approval_status = serializers.CharField(
        source="submission.approval_status",
        read_only=True
    )

    class Meta:
        model = Result
        fields = "__all__"

        read_only_fields = (
            "weighted_marks",
            "grade",
            "cbc_code",
            "cbc_description",
            "entered_by",
            "last_modified_by",
            "created_at",
            "updated_at",
        )

    def get_student_name(self, obj):

        if not obj.student:
            return None

        return str(obj.student)

    def get_assessment_name(self, obj):

        if not obj.submission:
            return None

        if not obj.submission.assessment:
            return None

        return str(obj.submission.assessment)

    def get_subject_name(self, obj):

        if not obj.submission:
            return None

        assessment = obj.submission.assessment

        if not assessment or not assessment.subject:
            return None

        return assessment.subject.name

    def get_classroom_name(self, obj):

        if not obj.submission:
            return None

        assessment = obj.submission.assessment

        if not assessment or not assessment.classroom:
            return None

        return str(assessment.classroom)

    def validate(self, attrs):

        submission = attrs.get("submission")
        marks = attrs.get("marks")
        result_status = attrs.get("status")

        if not submission:
            raise serializers.ValidationError(
                {
                    "submission":
                        "Result submission is required."
                }
            )

        assessment = submission.assessment

        if not assessment:
            raise serializers.ValidationError(
                {
                    "submission":
                        "This submission has no assessment assigned."
                }
            )

        # ----------------------------------------------------
        # ABSENT / EXCUSED / EXEMPTED / PENDING
        # ----------------------------------------------------

        if result_status in [
            Result.ResultStatus.ABSENT,
            Result.ResultStatus.EXCUSED,
            Result.ResultStatus.EXEMPTED,
            Result.ResultStatus.PENDING,
        ]:

            if marks is not None:
                raise serializers.ValidationError(
                    {
                        "marks":
                            "Marks must be empty when the learner is "
                            f"{result_status.lower()}."
                    }
                )

        # ----------------------------------------------------
        # PRESENT
        # ----------------------------------------------------

        if result_status == Result.ResultStatus.PRESENT:

            if marks is None:
                raise serializers.ValidationError(
                    {
                        "marks":
                            "Marks are required for a present learner."
                    }
                )

            if marks < 0:
                raise serializers.ValidationError(
                    {
                        "marks":
                            "Marks cannot be negative."
                    }
                )

            if marks > assessment.total_marks:
                raise serializers.ValidationError(
                    {
                        "marks":
                            f"Marks cannot exceed "
                            f"{assessment.total_marks}."
                    }
                )

        return attrs


# ============================================================
# BULK RESULT ITEM
# ============================================================

class BulkResultItemSerializer(serializers.Serializer):

    student = serializers.IntegerField()

    status = serializers.ChoiceField(
        choices=Result.ResultStatus.choices
    )

    marks = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True
    )

    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )

    def validate(self, attrs):

        status_value = attrs.get("status")
        marks = attrs.get("marks")

        if status_value == Result.ResultStatus.PRESENT:

            if marks is None:
                raise serializers.ValidationError(
                    {
                        "marks":
                            "Marks are required for a present learner."
                    }
                )

            if marks < 0:
                raise serializers.ValidationError(
                    {
                        "marks":
                            "Marks cannot be negative."
                    }
                )

        else:

            if marks is not None:
                raise serializers.ValidationError(
                    {
                        "marks":
                            "Marks must be empty when the learner "
                            "is not present."
                    }
                )

        return attrs


# ============================================================
# BULK RESULT
# ============================================================

class BulkResultSerializer(serializers.Serializer):

    submission = serializers.IntegerField()

    results = BulkResultItemSerializer(
        many=True
    )

    def validate_results(self, value):

        if not value:
            raise serializers.ValidationError(
                "At least one student result is required."
            )

        student_ids = [
            item["student"]
            for item in value
        ]

        if len(student_ids) != len(set(student_ids)):
            raise serializers.ValidationError(
                "The same student cannot appear more than once."
            )

        return value


# ============================================================
# STUDENT RESULT
# ============================================================

class StudentResultSerializer(serializers.ModelSerializer):

    student_name = serializers.SerializerMethodField(
        read_only=True
    )

    subject_name = serializers.CharField(
        source="subject.name",
        read_only=True
    )

    classroom_name = serializers.CharField(
        source="classroom.name",
        read_only=True
    )

    grade_name = serializers.CharField(
        source="grade.level",
        read_only=True
    )

    grade_description = serializers.CharField(
        source="grade.description",
        read_only=True
    )

    class Meta:
        model = StudentResult
        fields = "__all__"

    def get_student_name(self, obj):

        if not obj.student:
            return None

        return str(obj.student)


# ============================================================
# STUDENT TERM RESULT
# ============================================================

class StudentTermResultSerializer(serializers.ModelSerializer):

    student_name = serializers.SerializerMethodField(
        read_only=True
    )

    classroom_name = serializers.CharField(
        source="classroom.name",
        read_only=True
    )

    overall_grade_name = serializers.CharField(
        source="overall_grade.level",
        read_only=True
    )

    overall_grade_description = serializers.CharField(
        source="overall_grade.description",
        read_only=True
    )

    class Meta:
        model = StudentTermResult
        fields = "__all__"

    def get_student_name(self, obj):

        if not obj.student:
            return None

        return str(obj.student)


# ============================================================
# REPORT COMMENT
# ============================================================

class ReportCommentSerializer(serializers.ModelSerializer):

    grade_name = serializers.CharField(
        source="grade.level",
        read_only=True
    )

    class Meta:
        model = ReportComment
        fields = "__all__"

    def validate_comment(self, value):

        if not value.strip():
            raise serializers.ValidationError(
                "Comment cannot be empty."
            )

        return value


# ============================================================
# ASSESSMENT RUBRIC
# ============================================================

class AssessmentRubricSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssessmentRubric
        fields = "__all__"

    def validate(self, attrs):

        min_score = attrs.get("min_score")
        max_score = attrs.get("max_score")

        if min_score is not None and max_score is not None:

            if min_score > max_score:
                raise serializers.ValidationError(
                    {
                        "max_score":
                            "Maximum score cannot be lower than minimum score."
                    }
                )

        return attrs