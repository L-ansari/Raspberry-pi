"""Per-user data scoping helpers.

Authorization is implemented here as plain functions so the ``api`` and ``llm``
apps share one source of truth for who may read which sensor data.

A superuser is exempt from scoping and can see everything, including readings
that have no ``node_id`` (legacy/anonymous uploads) and nodes that have no owner
(e.g. nodes provisioned via the shared provisioning token).
"""

from .models import EdgeNode, SensorReading


def owned_node_ids(user):
    """Return the list of ``node_id`` values owned by ``user``.

    Returns ``None`` for a superuser to mean "no filtering". Returns an empty
    list for anonymous users or users that own no nodes (so they see nothing).
    """
    if user is None or not user.is_authenticated:
        return []
    if user.is_superuser:
        return None
    return list(
        EdgeNode.objects.filter(owner=user).values_list("node_id", flat=True)
    )


def readings_for_user(user):
    """Return the ``SensorReading`` queryset visible to ``user``."""
    node_ids = owned_node_ids(user)
    if node_ids is None:
        return SensorReading.objects.all()
    return SensorReading.objects.filter(node_id__in=node_ids)


def can_access_reading(user, reading):
    """Return True if ``user`` may access a single reading."""
    if user is not None and user.is_authenticated and user.is_superuser:
        return True
    if user is None or not user.is_authenticated:
        return False
    # Unowned readings (node_id is null) are visible only to superusers.
    if reading.node_id is None:
        return False
    return EdgeNode.objects.filter(
        owner=user, node_id=reading.node_id
    ).exists()
