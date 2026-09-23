from rest_framework import serializers


# =========================================================
# STUDENT SERIALIZERS
# =========================================================
class StudentSummarySerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    male_students = serializers.IntegerField()
    female_students = serializers.IntegerField()


class StudentsByClassSerializer(serializers.Serializer):
    classroom = serializers.CharField()
    total_students = serializers.IntegerField()


class StudentGenderReportSerializer(serializers.Serializer):
    gender = serializers.CharField(allow_null=True, allow_blank=True)
    total_students = serializers.IntegerField()


class NewAdmissionSerializer(serializers.Serializer):
    admission_number = serializers.CharField()
    student_name = serializers.CharField()
    classroom = serializers.CharField()
    date_admitted = serializers.DateField()


class StudentStatusReportSerializer(serializers.Serializer):
    status = serializers.CharField()
    total_students = serializers.IntegerField()


# =========================================================
# TEACHER SERIALIZERS
# =========================================================
class TeacherSummarySerializer(serializers.Serializer):
    total_teachers = serializers.IntegerField()
    male_teachers = serializers.IntegerField()
    female_teachers = serializers.IntegerField()


class TeachersByClassSerializer(serializers.Serializer):
    classroom = serializers.CharField()
    class_teacher = serializers.CharField(allow_null=True, allow_blank=True)


class TeachersBySubjectSerializer(serializers.Serializer):
    teacher = serializers.CharField()
    subject = serializers.CharField()
    classroom = serializers.CharField()
    term = serializers.CharField()


class TeacherWorkloadSerializer(serializers.Serializer):
    teacher = serializers.CharField()
    total_assignments = serializers.IntegerField()
    total_classes = serializers.IntegerField()
    total_subjects = serializers.IntegerField()


# =========================================================
# FEE SERIALIZERS
# =========================================================
class FeeSummarySerializer(serializers.Serializer):
    total_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class OutstandingBalanceSerializer(serializers.Serializer):
    admission_number = serializers.CharField()
    student_name = serializers.CharField()
    classroom = serializers.CharField()
    academic_year = serializers.IntegerField()
    term = serializers.CharField()
    total_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class FeeCollectionByTermSerializer(serializers.Serializer):
    academic_year = serializers.IntegerField()
    term = serializers.CharField()
    total_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class MonthlyFeeCollectionSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    total_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


# =========================================================
# PARENT SERIALIZERS
# =========================================================
class ParentSummarySerializer(serializers.Serializer):
    total_parents = serializers.IntegerField()
    parents_with_one_child = serializers.IntegerField()
    parents_with_multiple_children = serializers.IntegerField()


class ParentContactSerializer(serializers.Serializer):
    parent_name = serializers.CharField()
    phone_number = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    occupation = serializers.CharField(allow_blank=True)
    total_children = serializers.IntegerField()


class ParentChildSerializer(serializers.Serializer):
    admission_number = serializers.CharField()
    student_name = serializers.CharField()
    classroom = serializers.CharField()
    status = serializers.CharField()


class ParentChildrenSerializer(serializers.Serializer):
    parent_name = serializers.CharField()
    phone_number = serializers.CharField(allow_blank=True)
    total_children = serializers.IntegerField()
    children = ParentChildSerializer(many=True)


class ParentFeeReportSerializer(serializers.Serializer):
    parent_name = serializers.CharField()
    phone_number = serializers.CharField(allow_blank=True)
    total_children = serializers.IntegerField()
    total_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)


# =========================================================
# CLASS & SCHOOL SERIALIZERS
# =========================================================
class ClassCapacityReportSerializer(serializers.Serializer):
    classroom = serializers.CharField()
    capacity = serializers.IntegerField()
    current_students = serializers.IntegerField()
    available_spaces = serializers.IntegerField()


class SchoolSummarySerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_teachers = serializers.IntegerField()
    total_classes = serializers.IntegerField()
    total_subjects = serializers.IntegerField()


class DashboardStatisticsSerializer(serializers.Serializer):
    students = serializers.DictField()
    teachers = serializers.DictField()
    fees = FeeSummarySerializer()
    school = serializers.DictField()