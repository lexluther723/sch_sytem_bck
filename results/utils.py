from decimal import Decimal, InvalidOperation

from .models import GradeScale


# =====================================================
# Convert Score Safely
# =====================================================

def to_decimal(value, default=Decimal("0")):
    """
    Safely convert a value to Decimal.
    """

    if value is None:
        return default

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


# =====================================================
# CBC Grade Calculation
# =====================================================

def calculate_cbc_grade(score):
    """
    Calculate the Kenyan CBC performance level.

    Returns:
        (
            cbc_code,
            cbc_description
        )
    """

    score = to_decimal(score)

    if score >= Decimal("90"):
        return "EE1", "Exceeding Expectation"

    if score >= Decimal("75"):
        return "EE2", "Exceeding Expectation"

    if score >= Decimal("58"):
        return "ME1", "Meeting Expectation"

    if score >= Decimal("41"):
        return "ME2", "Meeting Expectation"

    if score >= Decimal("31"):
        return "AE1", "Approaching Expectation"

    if score >= Decimal("21"):
        return "AE2", "Approaching Expectation"

    if score >= Decimal("11"):
        return "BE1", "Below Expectation"

    if score >= Decimal("1"):
        return "BE2", "Below Expectation"

    return "N/A", "Not Assessed"


# =====================================================
# GradeScale Lookup
# =====================================================

def calculate_grade(score):
    """
    Return the GradeScale matching the supplied percentage.
    """

    score = to_decimal(score)

    return GradeScale.objects.filter(
        minimum_score__lte=score,
        maximum_score__gte=score,
    ).first()


# =====================================================
# Calculate Percentage
# =====================================================

def calculate_percentage(marks, total_marks):
    """
    Convert entered marks into a percentage.

    Example:

        marks = 45
        total_marks = 50

        result = 90

    If the assessment is out of 100:

        marks = 87
        total_marks = 100

        result = 87
    """

    marks = to_decimal(marks)
    total_marks = to_decimal(total_marks)

    if total_marks <= 0:
        return Decimal("0")

    percentage = (
        marks / total_marks
    ) * Decimal("100")

    return percentage.quantize(
        Decimal("0.01")
    )


# =====================================================
# Calculate Weighted Marks
# =====================================================

def calculate_weighted_marks(
    marks,
    total_marks,
    assessment_percentage=None,
):
    """
    Calculate the contribution of an assessment.

    IMPORTANT:

    The Results system currently treats the entered mark
    as being calculated against the assessment's own
    total_marks.

    Example:

        Assessment total = 100
        Student mark = 80

        percentage = 80%

    Example:

        Assessment total = 50
        Student mark = 40

        percentage = 80%

    If an assessment percentage is supplied, it can be
    used to calculate the weighted contribution.

    However, the normal result-entry calculation should
    use the assessment's actual total_marks.
    """

    percentage = calculate_percentage(
        marks,
        total_marks,
    )

    if assessment_percentage is None:
        return percentage

    assessment_percentage = to_decimal(
        assessment_percentage
    )

    weighted = (
        percentage
        * assessment_percentage
    ) / Decimal("100")

    return weighted.quantize(
        Decimal("0.01")
    )


# =====================================================
# Calculate Result Grade
# =====================================================

def calculate_result_grade(marks, total_marks):
    """
    Calculate all grading information for a result.

    Returns:

        {
            "percentage": ...,
            "grade": ...,
            "cbc_code": ...,
            "cbc_description": ...
        }
    """

    percentage = calculate_percentage(
        marks,
        total_marks,
    )

    grade = calculate_grade(
        percentage
    )

    cbc_code, cbc_description = calculate_cbc_grade(
        percentage
    )

    return {
        "percentage": percentage,
        "grade": grade,
        "cbc_code": cbc_code,
        "cbc_description": cbc_description,
    }


# =====================================================
# Get Report Comment
# =====================================================

def get_report_comment(grade):
    """
    Return the first configured report comment for
    a GradeScale.
    """

    if grade is None:
        return ""

    comment = grade.comments.first()

    if comment:
        return comment.comment

    return ""


# =====================================================
# Normalize Marks
# =====================================================

def normalize_marks(marks, total_marks):
    """
    Validate and normalize entered marks.

    The mark must be:

        >= 0
        <= assessment total_marks
    """

    marks = to_decimal(marks)
    total_marks = to_decimal(total_marks)

    if marks < 0:
        raise ValueError(
            "Marks cannot be negative."
        )

    if total_marks <= 0:
        raise ValueError(
            "Assessment total marks must be greater than zero."
        )

    if marks > total_marks:
        raise ValueError(
            f"Marks cannot exceed {total_marks}."
        )

    return marks


# =====================================================
# Result Percentage Helper
# =====================================================

def get_result_percentage(result):
    """
    Calculate the percentage represented by a Result.

    Example:

        Result marks = 72
        Assessment total = 100

        returns 72%

    Example:

        Result marks = 36
        Assessment total = 40

        returns 90%
    """

    if result is None:
        return Decimal("0")

    if result.marks is None:
        return Decimal("0")

    assessment = result.submission.assessment

    if assessment is None:
        return Decimal("0")

    return calculate_percentage(
        result.marks,
        assessment.total_marks,
    )