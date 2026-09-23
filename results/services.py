from decimal import Decimal

from django.db import transaction
from django.db.models import (
    Sum,
    Avg,
    Max,
    Min,
    Count,
)

from .models import (
    GradeScale,
    ResultSubmission,
    Result,
    StudentResult,
    StudentTermResult,
    ReportComment,
)

from .utils import calculate_cbc_grade


# ============================================================
# GRADE
# ============================================================

def get_grade(score):
    """
    Return the GradeScale matching a percentage score.
    """

    if score is None:
        return None

    score = Decimal(str(score))

    return GradeScale.objects.filter(
        minimum_score__lte=score,
        maximum_score__gte=score,
    ).first()


# ============================================================
# PERCENTAGE
# ============================================================

def calculate_percentage(marks, total_marks):
    """
    Convert marks obtained into a percentage.

    Examples:

        78 / 100 = 78%
        39 / 50  = 78%
        16 / 20  = 80%

    The teacher enters marks according to the actual
    assessment total marks.
    """

    if marks is None:
        return Decimal("0")

    if total_marks is None:
        return Decimal("0")

    total_marks = Decimal(str(total_marks))

    if total_marks <= 0:
        return Decimal("0")

    percentage = (
        Decimal(str(marks))
        / total_marks
    ) * Decimal("100")

    return percentage.quantize(
        Decimal("0.01")
    )


# ============================================================
# WEIGHTED MARKS
# ============================================================

def calculate_weighted_marks(result):
    """
    Calculate the normalized mark out of 100.

    IMPORTANT:

    There is NO assessment_type percentage here.

    The assessment's own total_marks determines the
    percentage.

    Example:

        Assessment = 50
        Student    = 40

        40 / 50 * 100 = 80
    """

    if result is None:
        return Decimal("0")

    if result.marks is None:
        return Decimal("0")

    if not result.submission:
        return Decimal("0")

    assessment = result.submission.assessment

    if not assessment:
        return Decimal("0")

    return calculate_percentage(
        result.marks,
        assessment.total_marks,
    )


# ============================================================
# PROCESS INDIVIDUAL RESULT
# ============================================================

def update_result(result):
    """
    Calculate the grade and CBC information for one
    assessment result.

    This only processes PRESENT learners with marks.

    Absent, Excused, Exempted and Pending learners do not
    receive a grade.
    """

    if not result:
        return result

    # --------------------------------------------------------
    # Non-present learners
    # --------------------------------------------------------

    if result.status != Result.ResultStatus.PRESENT:

        result.grade = None
        result.weighted_marks = Decimal("0")
        result.cbc_code = ""
        result.cbc_description = ""

        result.save(
            update_fields=[
                "grade",
                "weighted_marks",
                "cbc_code",
                "cbc_description",
                "updated_at",
            ]
        )

        return result

    # --------------------------------------------------------
    # Present but no marks
    # --------------------------------------------------------

    if result.marks is None:

        result.grade = None
        result.weighted_marks = Decimal("0")
        result.cbc_code = ""
        result.cbc_description = ""

        result.save(
            update_fields=[
                "grade",
                "weighted_marks",
                "cbc_code",
                "cbc_description",
                "updated_at",
            ]
        )

        return result

    # --------------------------------------------------------
    # Assessment
    # --------------------------------------------------------

    assessment = result.submission.assessment

    if not assessment:
        return result

    if assessment.total_marks <= 0:
        return result

    # --------------------------------------------------------
    # Calculate percentage
    # --------------------------------------------------------

    percentage = calculate_percentage(
        result.marks,
        assessment.total_marks,
    )

    # --------------------------------------------------------
    # Grade scale
    # --------------------------------------------------------

    grade = get_grade(
        percentage
    )

    # --------------------------------------------------------
    # CBC
    # --------------------------------------------------------

    cbc_code, cbc_description = calculate_cbc_grade(
        percentage
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result.grade = grade

    result.weighted_marks = percentage

    result.cbc_code = cbc_code

    result.cbc_description = cbc_description

    result.save(
        update_fields=[
            "grade",
            "weighted_marks",
            "cbc_code",
            "cbc_description",
            "updated_at",
        ]
    )

    return result


# ============================================================
# APPROVED RESULTS FOR ONE SUBJECT
# ============================================================

def get_approved_subject_results(
    student,
    subject,
    term,
    academic_year,
):
    """
    Return approved PRESENT assessment results for one
    student and subject during a term.
    """

    return Result.objects.filter(
        student=student,
        submission__assessment__subject=subject,
        submission__assessment__term=term,
        submission__assessment__academic_year=academic_year,
        submission__approval_status=(
            ResultSubmission.ApprovalStatus.APPROVED
        ),
        status=Result.ResultStatus.PRESENT,
        marks__isnull=False,
    ).select_related(
        "submission",
        "submission__assessment",
        "submission__assessment__subject",
        "grade",
    )


# ============================================================
# UPDATE SUBJECT RESULT
# ============================================================

def update_student_result(
    student,
    subject,
    classroom,
    term,
    academic_year,
):
    """
    Calculate the final subject result from all APPROVED
    assessments for the learner.

    Each assessment is first converted to a percentage
    according to its own total marks.

    Example:

        CAT 1: 40 / 50 = 80%
        CAT 2: 45 / 50 = 90%
        Exam : 70 / 100 = 70%

        Subject average:
        (80 + 90 + 70) / 3 = 80%
    """

    results = get_approved_subject_results(
        student=student,
        subject=subject,
        term=term,
        academic_year=academic_year,
    )

    if not results.exists():

        StudentResult.objects.filter(
            student=student,
            subject=subject,
            classroom=classroom,
            term=term,
            academic_year=academic_year,
        ).delete()

        return None

    # --------------------------------------------------------
    # Make sure every result has current calculations
    # --------------------------------------------------------

    for result in results:

        update_result(result)

    # Re-fetch because update_result modified the objects.
    results = get_approved_subject_results(
        student=student,
        subject=subject,
        term=term,
        academic_year=academic_year,
    )

    # --------------------------------------------------------
    # Total and average
    # --------------------------------------------------------

    total = results.aggregate(
        total=Sum("weighted_marks")
    )["total"] or Decimal("0")

    average = results.aggregate(
        average=Avg("weighted_marks")
    )["average"] or Decimal("0")

    average = Decimal(str(average)).quantize(
        Decimal("0.01")
    )

    # --------------------------------------------------------
    # Grade
    # --------------------------------------------------------

    grade = get_grade(
        average
    )

    # --------------------------------------------------------
    # CBC
    # --------------------------------------------------------

    cbc_code, cbc_description = calculate_cbc_grade(
        average
    )

    # --------------------------------------------------------
    # Teacher comment
    # --------------------------------------------------------

    teacher_comment = get_report_comment(
        grade
    )

    # --------------------------------------------------------
    # Save final subject result
    # --------------------------------------------------------

    student_result, _ = (
        StudentResult.objects.update_or_create(

            student=student,

            subject=subject,

            classroom=classroom,

            term=term,

            academic_year=academic_year,

            defaults={
                "total_score": total,
                "average_score": average,
                "grade": grade,
                "cbc_code": cbc_code,
                "cbc_description": cbc_description,
                "teacher_comment": teacher_comment,
            },
        )
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    update_subject_positions(
        subject=subject,
        classroom=classroom,
        term=term,
        academic_year=academic_year,
    )

    update_subject_statistics(
        subject=subject,
        classroom=classroom,
        term=term,
        academic_year=academic_year,
    )

    return student_result


# ============================================================
# UPDATE TERM RESULT
# ============================================================

def update_student_term_result(
    student,
    classroom,
    term,
    academic_year,
):
    """
    Calculate the learner's overall term result from all
    final subject results.
    """

    subject_results = StudentResult.objects.filter(
        student=student,
        classroom=classroom,
        term=term,
        academic_year=academic_year,
    )

    if not subject_results.exists():

        StudentTermResult.objects.filter(
            student=student,
            classroom=classroom,
            term=term,
            academic_year=academic_year,
        ).delete()

        return None

    # --------------------------------------------------------
    # Total subject scores
    # --------------------------------------------------------

    total_marks = subject_results.aggregate(
        total=Sum("average_score")
    )["total"] or Decimal("0")

    # --------------------------------------------------------
    # Average across subjects
    # --------------------------------------------------------

    average = subject_results.aggregate(
        average=Avg("average_score")
    )["average"] or Decimal("0")

    average = Decimal(str(average)).quantize(
        Decimal("0.01")
    )

    # --------------------------------------------------------
    # Overall grade
    # --------------------------------------------------------

    grade = get_grade(
        average
    )

    # --------------------------------------------------------
    # CBC
    # --------------------------------------------------------

    cbc_code, cbc_description = calculate_cbc_grade(
        average
    )

    # --------------------------------------------------------
    # Class teacher comment
    # --------------------------------------------------------

    class_teacher_comment = get_report_comment(
        grade
    )

    # --------------------------------------------------------
    # Create/update term result
    # --------------------------------------------------------

    term_result, _ = (
        StudentTermResult.objects.update_or_create(

            student=student,

            classroom=classroom,

            academic_year=academic_year,

            term=term,

            defaults={
                "total_marks": total_marks,
                "average_marks": average,
                "overall_grade": grade,
                "cbc_code": cbc_code,
                "cbc_description": cbc_description,
                "class_teacher_comment":
                    class_teacher_comment,
                "total_subjects":
                    subject_results.count(),
            },
        )
    )

    return term_result


# ============================================================
# PROCESS ONE RESULT
# ============================================================

def process_result(result):
    """
    Process one result after it has been saved.

    This function:

        1. Calculates the assessment percentage.
        2. Calculates the grade.
        3. Calculates CBC code.
        4. Updates the final subject result.
        5. Updates the overall term result.
        6. Updates class positions.
        7. Updates subject positions.
        8. Updates subject statistics.

    IMPORTANT:

    This function is called explicitly by views/services.

    There is NO Django signal involved.
    """

    if not result:
        return None

    submission = result.submission

    if not submission:
        return None

    assessment = submission.assessment

    if not assessment:
        return None

    # --------------------------------------------------------
    # Only approved submissions become final results.
    # --------------------------------------------------------

    if submission.approval_status != (
        ResultSubmission.ApprovalStatus.APPROVED
    ):

        return result

    with transaction.atomic():

        # ----------------------------------------------------
        # Process individual assessment result
        # ----------------------------------------------------

        update_result(
            result
        )

        # ----------------------------------------------------
        # Process subject
        # ----------------------------------------------------

        update_student_result(
            student=result.student,
            subject=assessment.subject,
            classroom=assessment.classroom,
            term=assessment.term,
            academic_year=assessment.academic_year,
        )

        # ----------------------------------------------------
        # Process overall term
        # ----------------------------------------------------

        update_student_term_result(
            student=result.student,
            classroom=assessment.classroom,
            term=assessment.term,
            academic_year=assessment.academic_year,
        )

        # ----------------------------------------------------
        # Class ranking
        # ----------------------------------------------------

        update_class_positions(
            classroom=assessment.classroom,
            term=assessment.term,
            academic_year=assessment.academic_year,
        )

        # ----------------------------------------------------
        # Subject ranking
        # ----------------------------------------------------

        update_subject_positions(
            subject=assessment.subject,
            classroom=assessment.classroom,
            term=assessment.term,
            academic_year=assessment.academic_year,
        )

        # ----------------------------------------------------
        # Subject statistics
        # ----------------------------------------------------

        update_subject_statistics(
            subject=assessment.subject,
            classroom=assessment.classroom,
            term=assessment.term,
            academic_year=assessment.academic_year,
        )

    return result


# ============================================================
# PROCESS ENTIRE SUBMISSION
# ============================================================

def process_submission(submission):
    """
    Process every result belonging to an approved submission.

    This replaces the old post_save ResultSubmission signal.
    """

    if not submission:
        return

    if submission.approval_status != (
        ResultSubmission.ApprovalStatus.APPROVED
    ):

        return

    results = submission.results.select_related(
        "student",
        "submission",
        "submission__assessment",
        "submission__assessment__subject",
        "submission__assessment__classroom",
        "grade",
    ).all()

    with transaction.atomic():

        for result in results:

            process_result(
                result
            )


# ============================================================
# CLASS POSITIONS
# ============================================================

def update_class_positions(
    classroom,
    term,
    academic_year,
):
    """
    Calculate competition ranking.

    Example:

        90 -> 1
        90 -> 1
        85 -> 3
        80 -> 4
    """

    results = StudentTermResult.objects.filter(
        classroom=classroom,
        term=term,
        academic_year=academic_year,
    ).order_by(
        "-average_marks",
        "student__last_name",
        "student__first_name",
    )

    previous_average = None
    current_position = 0
    row_number = 0

    for result in results:

        row_number += 1

        if previous_average != result.average_marks:

            current_position = row_number

        if result.position != current_position:

            result.position = current_position

            result.save(
                update_fields=[
                    "position",
                    "updated_at",
                ]
            )

        previous_average = result.average_marks


# ============================================================
# SUBJECT POSITIONS
# ============================================================

def update_subject_positions(
    subject,
    classroom,
    term,
    academic_year,
):
    """
    Calculate competition ranking for one subject.

    Example:

        95 -> 1
        95 -> 1
        90 -> 3
        87 -> 4
    """

    results = StudentResult.objects.filter(
        subject=subject,
        classroom=classroom,
        term=term,
        academic_year=academic_year,
    ).order_by(
        "-average_score",
        "student__last_name",
        "student__first_name",
    )

    previous_score = None
    current_position = 0
    row_number = 0

    for result in results:

        row_number += 1

        if previous_score != result.average_score:

            current_position = row_number

        if result.subject_position != current_position:

            result.subject_position = current_position

            result.save(
                update_fields=[
                    "subject_position",
                ]
            )

        previous_score = result.average_score


# ============================================================
# SUBJECT STATISTICS
# ============================================================

def update_subject_statistics(
    subject,
    classroom,
    term,
    academic_year,
):
    """
    Calculate:

        highest score
        lowest score
        class average
        number of learners assessed
    """

    queryset = StudentResult.objects.filter(
        subject=subject,
        classroom=classroom,
        term=term,
        academic_year=academic_year,
    )

    if not queryset.exists():
        return

    statistics = queryset.aggregate(
        highest=Max("average_score"),
        lowest=Min("average_score"),
        average=Avg("average_score"),
        assessed=Count("id"),
    )

    queryset.update(
        highest_score=statistics["highest"] or Decimal("0"),
        lowest_score=statistics["lowest"] or Decimal("0"),
        class_average=statistics["average"] or Decimal("0"),
        learners_assessed=statistics["assessed"] or 0,
    )


# ============================================================
# REPORT COMMENT
# ============================================================

def get_report_comment(grade):
    """
    Return the first automatic report comment associated
    with the learner's grade.
    """

    if grade is None:
        return ""

    comment = (
        ReportComment.objects
        .filter(grade=grade)
        .first()
    )

    if comment:
        return comment.comment

    return ""