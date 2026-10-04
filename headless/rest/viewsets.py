from django.db import IntegrityError, models, transaction
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.mixins import (
    CreateModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


class SingletonViewSet(
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
            raise

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
