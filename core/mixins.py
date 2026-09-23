"""
Reusable mixins that let one endpoint serve several frontend needs,
instead of the frontend making several requests or the backend
growing several near-duplicate endpoints.
"""

from rest_framework import serializers


class DynamicFieldsMixin:
    """
    Add to any ModelSerializer to support `?fields=a,b,c` and
    `?exclude=d,e`.

    WHY: several apps had (or were tempted to add) a "light" list
    serializer and a "full" detail serializer for the same model
    just to avoid sending unused fields down the wire (e.g.
    `StudentListSerializer` vs `StudentSerializer`). That's an extra
    class + extra endpoint surface to maintain per model.

    With this mixin, ONE serializer can do both jobs:
        GET /students/?fields=id,first_name,last_name   -> light list
        GET /students/42/                                -> full detail
    without the client needing a second round trip to fetch fields it
    left out the first time, and without us hand-maintaining two
    serializers that drift out of sync.

    Usage:
        class StudentSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
            class Meta:
                model = Student
                fields = [...]  # the FULL field set
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request is not None:
            fields = request.query_params.get("fields", fields)
            exclude = request.query_params.get("exclude")
        else:
            exclude = None

        if fields:
            allowed = set(f.strip() for f in fields.split(",") if f.strip())
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name, None)

        if exclude:
            for field_name in (f.strip() for f in exclude.split(",")):
                self.fields.pop(field_name, None)


class SelectRelatedListMixin:
    """
    Small guardrail, not a magic optimizer: forces every subclass of
    a `ListAPIView`/`ModelViewSet` to explicitly declare
    `select_related_fields` / `prefetch_related_fields` and applies
    them in `get_queryset()`, so query optimization isn't something
    that quietly gets forgotten when a new list view is added.

    Usage:
        class MyListView(SelectRelatedListMixin, generics.ListAPIView):
            queryset = MyModel.objects.all()
            select_related_fields = ("classroom", "parent__user")
            prefetch_related_fields = ("subjects",)
    """

    select_related_fields = ()
    prefetch_related_fields = ()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)
        return qs


class MultiSerializerMixin:
    """
    Lets one view (typically a ModelViewSet) reuse itself across
    actions instead of splitting list/create/retrieve into separate
    view classes with duplicated permission/queryset logic.

    Usage:
        class ThingViewSet(MultiSerializerMixin, viewsets.ModelViewSet):
            serializer_class = ThingDetailSerializer          # default
            serializer_action_map = {
                "list": ThingListSerializer,                  # lighter, for lists
            }
    """

    serializer_action_map = {}

    def get_serializer_class(self):
        return self.serializer_action_map.get(self.action, self.serializer_class)
