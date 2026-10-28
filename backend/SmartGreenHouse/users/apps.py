from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth.management import create_permissions


class UsersConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = 'users'

    def ready(self):
        # Workaround for a django-mongodb-backend incompatibility: Django's
        # `create_permissions` post_migrate receiver relies on auto-increment
        # primary-key semantics. On a fresh database (or whenever a new
        # ContentType is created) it builds a set of ContentType instances whose
        # primary key is still None, and crashes with "Model instances without
        # primary key value are unhashable", breaking both `migrate` and
        # `manage.py test`.
        #
        # This project does not use Django's Permission model at all:
        # authentication is JWT-based and authorization is implemented via
        # per-node ownership scoping. Disconnecting the receiver is therefore
        # lossless here while keeping migrations and tests runnable.
        post_migrate.disconnect(
            create_permissions,
            dispatch_uid="django.contrib.auth.management.create_permissions",
        )

