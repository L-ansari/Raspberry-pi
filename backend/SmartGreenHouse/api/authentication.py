import hashlib
import secrets

from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import EdgeNode


def generate_api_key():
    """Return a random per-node API key to hand to a device exactly once."""
    return secrets.token_urlsafe(32)


def hash_api_key(key):
    """Return the SHA-256 hex digest used to store and match an API key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class EdgeNodeKeyAuthentication(BaseAuthentication):
    """
    Authenticate an edge device via the ``X-Edge-Key`` header.

    Returns ``None`` when the header is absent so legacy (anonymous) sensor
    clients keep working. When the header is present, it must map to a known,
    enabled ``EdgeNode``; otherwise authentication fails.
    """

    def authenticate(self, request):
        raw_key = request.META.get("HTTP_X_EDGE_KEY")
        if not raw_key:
            return None

        key_hash = hash_api_key(raw_key)
        try:
            node = EdgeNode.objects.get(api_key_hash=key_hash)
        except EdgeNode.DoesNotExist:
            raise AuthenticationFailed("Invalid edge API key.")

        if node.status == EdgeNode.Status.DISABLED:
            raise AuthenticationFailed("Edge node is disabled.")

        request.edge_node = node
        return (AnonymousUser(), node)

    def authenticate_header(self, request):
        return "Edge"
