from contextlib import contextmanager

from django.db import IntegrityError, models, transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    CreateModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
)
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet

CONSTRAINT_ERROR_MESSAGE = "The data conflicts with a database constraint."


@contextmanager
def constraint_errors_as_validation_errors():
    """
    Turn a database constraint violation (IntegrityError) into a 400
    validation error with a fixed message, so the database's error text
    stays internal. The block runs in a savepoint, so the surrounding
    transaction (e.g. with ATOMIC_REQUESTS) stays usable.
    """
    try:
        with transaction.atomic():
            yield
    except IntegrityError:
        raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [CONSTRAINT_ERROR_MESSAGE]})


class ConstraintErrorMixin:
    """
    Answer 400 instead of 500 when a create or update violates a database
    constraint that the serializer does not validate, such as a
    CheckConstraint.
    """

    def perform_create(self, serializer):
        with constraint_errors_as_validation_errors():
            super().perform_create(serializer)

    def perform_update(self, serializer):
        with constraint_errors_as_validation_errors():
            super().perform_update(serializer)


class ExpandPrefetchMixin:
    """
    Prefetch the relations requested with ?expand=, so that expanding a
    relation costs one query per relation instead of one per object.
    Only applies to serializers with expandable fields (FlexibleSerializer).
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        request = getattr(self, "request", None)

        # Only DRF requests carry query_params
        if getattr(request, "query_params", None) is None:
            return queryset

        prefetch_paths = self.get_expand_prefetch_paths(request)
        return queryset.prefetch_related(*prefetch_paths) if prefetch_paths else queryset

    def get_expand_prefetch_paths(self, request):
        """
        Return the ORM paths (e.g. "category__articles") of the relations
        requested with ?expand=. Only paths of expandable relations are
        returned; anything else is left to the serializer to ignore.
        """
        from rest_flex_fields import EXPAND_PARAM, WILDCARD_VALUES

        values = request.query_params.getlist(EXPAND_PARAM) or request.query_params.getlist(f"{EXPAND_PARAM}[]")
        if len(values) == 1:
            values = values[0].split(",")

        serializer_class = self.get_serializer_class()
        paths = []

        for value in values:
            names = value.split(".")
            if names[0] in (WILDCARD_VALUES or []):
                names = None
            paths.extend(self._resolve_prefetch_paths(serializer_class, names))

        return list(dict.fromkeys(paths))

    def _resolve_prefetch_paths(self, serializer_class, names, prefix=""):
        """
        Resolve an expand path (a list of names, or None for all expandable
        relations at this level) against the expandable fields of the
        serializer class, level by level.
        """
        expandable_fields = getattr(serializer_class(), "_expandable_fields", None)
        if not expandable_fields:
            return []

        if names is None:
            return [f"{prefix}{name}" for name in expandable_fields]

        name, rest = names[0], names[1:]
        if name not in expandable_fields:
            return []

        path = f"{prefix}{name}"
        if not rest:
            return [path]

        nested_paths = self._resolve_prefetch_paths(expandable_fields[name][0], rest, f"{path}__")
        return nested_paths or [path]


class SingletonViewSet(
    ConstraintErrorMixin,
    ExpandPrefetchMixin,
    GenericViewSet,
    CreateModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
):
    """
    A model view set for singleton objects.
    """

    def get_object(self):
        """
        Get the first object of the queryset (assuming there is only one object).
        If a singleton doesn't exist, it will raise a NotFound exception.
        """
        obj = self.get_singleton_queryset().first()

        if obj is None:
            raise NotFound()

        self.check_object_permissions(self.request, obj)

        return obj

    def update(self, request, *args, **kwargs):
        """
        Update the singleton. If a singleton doesn't exist, it will be created.
        """
        partial = kwargs.pop("partial", False)

        # Update the existing singleton if there is one. The row is locked
        # for the duration of the transaction, serializing concurrent updates.
        with transaction.atomic():
            instance = self.get_locked_singleton()
            if instance is not None:
                return self._perform_update(instance, request, partial)

        # No singleton exists yet: create one. When the model has an auto
        # primary key, the instance is created with a deterministic pk so that
        # concurrent requests cannot create more than one singleton: only
        # one insert can win the primary key constraint.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pk = self.get_singleton_pk()

        try:
            with transaction.atomic():
                serializer.save(**({"pk": pk} if pk is not None else {}))
        except IntegrityError:
            # A concurrent request created the singleton first: update it.
            with transaction.atomic():
                instance = self.get_locked_singleton()
                if instance is not None:
                    return self._perform_update(instance, request, partial)
            # No singleton exists, so the data itself violates a constraint
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [CONSTRAINT_ERROR_MESSAGE]})

        if pk is not None:
            # Inserting an explicit pk does not advance the auto pk sequence.
            # Reset it so later ORM inserts don't collide with the singleton.
            self._reset_pk_sequence()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(serializer.data),
        )

    def get_singleton_queryset(self):
        """
        Return the queryset for the singleton. Ordered by pk so that the
        "first" instance is deterministic even without model ordering.
        """
        return self.get_queryset().order_by("pk")

    def get_locked_singleton(self):
        """
        Return the singleton instance, locked for the duration of the
        surrounding transaction. Returns None if no singleton exists yet.
        """
        return self.get_singleton_queryset().select_for_update().first()

    def get_singleton_pk(self):
        """
        Return a deterministic primary key for creating the singleton, or
        None when the model does not use an auto primary key (in which case
        creation is left to the database and is not race-safe).
        """
        pk_field = self.get_queryset().model._meta.pk
        if isinstance(pk_field, (models.AutoField, models.BigAutoField, models.SmallAutoField)):
            return 1
        return None

    def _perform_update(self, instance, request, partial):
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects", None):
            instance._prefetched_objects = None

        return Response(serializer.data)

    def _reset_pk_sequence(self):
        """
        Sync the auto pk sequence with the explicitly inserted singleton pk.
        """
        from django.core.management.color import no_style
        from django.db import connection

        model = self.get_queryset().model
        sql_list = connection.ops.sequence_reset_sql(no_style(), [model])
        with connection.cursor() as cursor:
            for sql in sql_list:
                cursor.execute(sql)


class LookupFieldsMixin:
    """
    Adds retrieve routes by unique fields (by_<field>/<value>) to a model
    view set. These routes are retrieves by another key: view.action is
    "retrieve" for them, so action-based permissions, serializers and
    throttles apply as they do to the detail route. view.lookup_by holds
    the field the request looks up by.
    """

    # Maps the lookup action names to the field they look up by
    lookup_actions = {}
    # The field the current request looks up by; None on other routes
    lookup_by = None

    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)

        # The action is resolved here, before permissions are checked
        lookup_by = self.lookup_actions.get(self.action)
        if lookup_by is not None:
            self.action = "retrieve"
            self.lookup_by = lookup_by

        return request

    def retrieve_by_lookup(self, request, value):
        """
        Retrieve a single object by the lookup field, mirroring retrieve.
        """
        queryset = self.filter_queryset(self.get_queryset())
        # DRF's get_object_or_404 also returns 404 for values that cannot
        # be cast to the field's type (e.g. a malformed UUID).
        instance = get_object_or_404(queryset, **{self.lookup_by: value})
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
