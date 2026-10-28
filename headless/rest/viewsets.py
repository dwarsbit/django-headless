from contextlib import contextmanager

from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, models, transaction
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    CreateModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import SAFE_METHODS
from rest_framework.relations import ManyRelatedField
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer
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


class RelatedLoadingMixin:
    """
    Load the relations a read request serializes with a fixed number of
    queries, instead of one query per object:

    - Relations requested with ?expand= are joined (forward foreign keys
      and one-to-one fields) or prefetched (everything else).
    - Many-valued relations serialized as primary keys, such as
      many-to-many fields, are prefetched.

    Relations left out of the response with ?fields= or ?omit= are not
    loaded. Only applies to safe (read) requests. Expanding relations
    requires a serializer with expandable fields (FlexibleSerializer).
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        request = getattr(self, "request", None)

        # Only DRF requests carry query_params. Writes are left alone, so
        # their responses never show relations cached before the change.
        if getattr(request, "query_params", None) is None or request.method not in SAFE_METHODS:
            return queryset

        select_paths, prefetch_paths = self.get_related_paths(request)
        if select_paths:
            queryset = queryset.select_related(*select_paths)
        if prefetch_paths:
            queryset = queryset.prefetch_related(*prefetch_paths)

        return queryset

    def get_related_paths(self, request):
        """
        Return the ORM paths (e.g. "category__articles") of the relations to
        load for a request, as a (select_related, prefetch_related) tuple.
        Only paths of expandable relations are returned for ?expand=;
        anything else is left to the serializer to ignore. Relations that
        ?fields= or ?omit= leave out of the response are skipped.
        """
        from rest_flex_fields import EXPAND_PARAM, FIELDS_PARAM, OMIT_PARAM, WILDCARD_VALUES

        serializer_class = self.get_serializer_class()
        expansions = [value.split(".") for value in self._get_list_param(request, EXPAND_PARAM)]

        # A wildcard expands every expandable relation of the first level
        if any(names[0] in (WILDCARD_VALUES or []) for names in expansions):
            expandable_fields = getattr(serializer_class(), "_expandable_fields", None) or {}
            expansions = [[name] for name in expandable_fields]

        sparse = self._get_list_param(request, FIELDS_PARAM)
        omit = self._get_list_param(request, OMIT_PARAM)

        select_paths, prefetch_paths = [], []
        self._collect_related_paths(serializer_class, expansions, sparse, omit, "", True, select_paths, prefetch_paths)

        return list(dict.fromkeys(select_paths)), list(dict.fromkeys(prefetch_paths))

    @staticmethod
    def _get_list_param(request, name):
        """
        Return the values of a drf-flex-fields query parameter, parsed as
        drf-flex-fields does: repeated (also as name[]) or comma-separated.
        """
        values = request.query_params.getlist(name) or request.query_params.getlist(f"{name}[]")
        if len(values) == 1:
            values = values[0].split(",")

        return [value for value in values if value]

    def _collect_related_paths(
        self, serializer_class, expansions, sparse, omit, prefix, joinable, select_paths, prefetch_paths
    ):
        """
        Collect the paths to load for a serializer class, level by level.
        expansions holds the expand paths (as lists of names) that start at
        this level, sparse and omit the ?fields= and ?omit= values (dotted
        strings) that apply to it. A relation can be joined only when every
        relation on its path can be: a join cannot go through a many-valued
        relation.
        """
        from rest_flex_fields.serializers import FlexFieldsSerializerMixin
        from rest_flex_fields.utils import split_levels

        # Only flex-fields serializers apply fields and omit
        if not issubclass(serializer_class, FlexFieldsSerializerMixin):
            sparse, omit = [], []

        sparse_fields, next_sparse = split_levels(sparse)
        omit_fields, next_omit = split_levels(omit)

        def is_included(name):
            return self._is_included(name, sparse_fields, omit_fields, next_omit)

        for name, source in self._get_to_many_names(serializer_class):
            if is_included(name):
                prefetch_paths.append(f"{prefix}{source}")

        expandable_fields = getattr(serializer_class(), "_expandable_fields", None)
        if not expandable_fields:
            return

        children = {}
        for names in expansions:
            children.setdefault(names[0], []).append(names[1:])

        for name, rests in children.items():
            if name not in expandable_fields or not is_included(name):
                continue

            path = f"{prefix}{name}"
            can_join = joinable and self._is_joinable(serializer_class, name)
            (select_paths if can_join else prefetch_paths).append(path)

            nested = [rest for rest in rests if rest]
            self._collect_related_paths(
                expandable_fields[name][0],
                nested,
                next_sparse.get(name, []),
                next_omit.get(name, []),
                f"{path}__",
                can_join,
                select_paths,
                prefetch_paths,
            )

    @staticmethod
    def _is_included(name, sparse_fields, omit_fields, next_omit):
        """
        Check whether a field of a level is in the response, as
        drf-flex-fields decides it: an omitted field is left out unless only
        its nested fields are omitted (omit=a.b keeps a), and a sparse
        fieldset without a wildcard keeps only the fields it names.
        """
        from rest_flex_fields import WILDCARD_VALUES

        if name in omit_fields and name not in next_omit:
            return False
        if set(sparse_fields) & set(WILDCARD_VALUES or []):
            return True
        return not sparse_fields or name in sparse_fields

    @staticmethod
    def _is_joinable(serializer_class, name):
        """
        Check whether a relation can be loaded with a join: a forward foreign
        key or one-to-one field of the serializer's model.
        """
        try:
            field = serializer_class.Meta.model._meta.get_field(name)
        except (AttributeError, FieldDoesNotExist):
            return False

        return field.concrete and (field.many_to_one or field.one_to_one)

    @staticmethod
    def _get_to_many_names(serializer_class):
        """
        Return the many-valued relations (many-to-many fields and reverse
        foreign keys) that a serializer class reads, as (field name, model
        attribute) tuples.
        """
        model = getattr(getattr(serializer_class, "Meta", None), "model", None)
        if model is None:
            return []

        names = []
        for name, field in serializer_class().fields.items():
            if field.write_only or not isinstance(field, (ManyRelatedField, ListSerializer)):
                continue

            source_attrs = field.source_attrs
            if len(source_attrs) == 1 and isinstance(getattr(model, source_attrs[0], None), ReverseManyToOneDescriptor):
                names.append((name, source_attrs[0]))

        return names


class SingletonViewSet(
    ConstraintErrorMixin,
    RelatedLoadingMixin,
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
