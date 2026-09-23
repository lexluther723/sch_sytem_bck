"""
RETIRED - intentionally left empty.

This module defined three signal receivers that maintained the
denormalised `ClassRoom.total_students` counter. It was never imported
by anything (students/apps.py has no ready()), so the receivers never
connected and the counter was permanently 0.

`total_students` is now computed from the database in
classes/serializers.py via an annotated `Count("students")`, which
cannot drift out of sync and costs no extra queries. Reconnecting
these receivers would double-count.

Kept as an empty module rather than deleted so that any stray import
does not raise ImportError.
"""
