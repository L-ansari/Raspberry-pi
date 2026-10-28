from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import EdgeNode, SensorReading

User = get_user_model()

PROVISIONING_TOKEN = "test-provisioning-token"
ALLOWED_ZONES = ["zone-1", "zone-2"]


class EdgeTestCase(APITransactionTestCase):
    """Base helpers. APITransactionTestCase is used because the MongoDB backend
    does not support transaction-based rollback used by TestCase."""

    def _create_user(self, username="tester", password="secret-pass-123"):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=password,
        )

    def _create_superuser(self, username="admin", password="secret-pass-123"):
        return User.objects.create_superuser(
            username=username,
            email=f"{username}@example.com",
            password=password,
        )

    def _access_token(self, user=None):
        user = user or self._create_user()
        return str(RefreshToken.for_user(user).access_token)

    def _register_node(self, node_id="node-001", name="Node 1", zone_id="zone-1"):
        """Register a node using the provisioning token (owner=None); returns the API key."""
        response = self.client.post(
            "/api/edges/register/",
            {
                "node_id": node_id,
                "name": name,
                "zone_id": zone_id,
                "provisioning_token": PROVISIONING_TOKEN,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        return response.data["api_key"]

    def _register_node_as(self, user, node_id="node-001", name="Node 1", zone_id="zone-1"):
        """Register a node while authenticated as ``user`` (owner=user); returns the API key."""
        token = self._access_token(user)
        response = self.client.post(
            "/api/edges/register/",
            {"node_id": node_id, "name": name, "zone_id": zone_id},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 201, response.data
        return response.data["api_key"]

    def _create_reading(self, api_key=None, **overrides):
        payload = {
            "temperature": 21.5,
            "humidity": 55.0,
            "soil_moisture": 40.0,
            "light": 720,
        }
        payload.update(overrides)
        kwargs = {"format": "json"}
        if api_key:
            kwargs["HTTP_X_EDGE_KEY"] = api_key
        response = self.client.post("/api/sensors/", payload, **kwargs)
        assert response.status_code == 201, response.data
        return response.data


@override_settings(
    EDGE_PROVISIONING_TOKEN=PROVISIONING_TOKEN,
    EDGE_ALLOWED_ZONES=ALLOWED_ZONES,
)
class EdgeNodeRegistrationTests(EdgeTestCase):
    def test_register_success_with_provisioning_token(self):
        response = self.client.post(
            "/api/edges/register/",
            {
                "node_id": "node-001",
                "name": "Node 1",
                "zone_id": "zone-1",
                "provisioning_token": PROVISIONING_TOKEN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["node"]["node_id"], "node-001")
        self.assertEqual(response.data["node"]["zone_id"], "zone-1")
        self.assertEqual(response.data["node"]["status"], "offline")
        self.assertIn("api_key", response.data)
        # The plaintext key and its hash never appear inside the node record.
        self.assertNotIn("api_key", response.data["node"])
        self.assertNotIn("api_key_hash", response.data["node"])

        node = EdgeNode.objects.get(node_id="node-001")
        self.assertEqual(node.status, EdgeNode.Status.OFFLINE)
        # Provisioning-token registration creates an unowned node.
        self.assertIsNone(node.owner)

    def test_register_success_with_jwt(self):
        user = self._create_user("owner-user")
        token = self._access_token(user)
        response = self.client.post(
            "/api/edges/register/",
            {"node_id": "node-jwt", "name": "JWT Node", "zone_id": "zone-1"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        node = EdgeNode.objects.get(node_id="node-jwt")
        self.assertEqual(node.owner, user)

    def test_register_duplicate_node_id(self):
        self._register_node("node-dup")
        response = self.client.post(
            "/api/edges/register/",
            {
                "node_id": "node-dup",
                "name": "Duplicate",
                "zone_id": "zone-1",
                "provisioning_token": PROVISIONING_TOKEN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_register_invalid_zone(self):
        response = self.client.post(
            "/api/edges/register/",
            {
                "node_id": "node-badzone",
                "name": "Bad Zone",
                "zone_id": "not-a-zone",
                "provisioning_token": PROVISIONING_TOKEN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("zone_id", response.data["errors"])

    def test_register_missing_fields(self):
        response = self.client.post(
            "/api/edges/register/",
            {"node_id": "node-noname", "provisioning_token": PROVISIONING_TOKEN},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data["errors"])
        self.assertIn("zone_id", response.data["errors"])

    def test_register_unauthorized(self):
        response = self.client.post(
            "/api/edges/register/",
            {"node_id": "node-anon", "name": "Anon", "zone_id": "zone-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(EdgeNode.objects.filter(node_id="node-anon").exists())


@override_settings(
    EDGE_PROVISIONING_TOKEN=PROVISIONING_TOKEN,
    EDGE_ALLOWED_ZONES=ALLOWED_ZONES,
)
class EdgeHeartbeatTests(EdgeTestCase):
    def test_heartbeat_authorized(self):
        api_key = self._register_node("node-hb")
        response = self.client.post(
            "/api/edges/heartbeat/", {}, format="json", HTTP_X_EDGE_KEY=api_key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "online")

        node = EdgeNode.objects.get(node_id="node-hb")
        self.assertEqual(node.status, EdgeNode.Status.ONLINE)
        self.assertIsNotNone(node.last_heartbeat)

    def test_heartbeat_unknown_key(self):
        response = self.client.post(
            "/api/edges/heartbeat/", {}, format="json", HTTP_X_EDGE_KEY="bogus"
        )
        self.assertEqual(response.status_code, 401)

    def test_heartbeat_disabled_node(self):
        api_key = self._register_node("node-disabled")
        node = EdgeNode.objects.get(node_id="node-disabled")
        node.status = EdgeNode.Status.DISABLED
        node.save()

        response = self.client.post(
            "/api/edges/heartbeat/", {}, format="json", HTTP_X_EDGE_KEY=api_key
        )
        self.assertEqual(response.status_code, 401)


@override_settings(
    EDGE_PROVISIONING_TOKEN=PROVISIONING_TOKEN,
    EDGE_ALLOWED_ZONES=ALLOWED_ZONES,
)
class EdgeListingTests(EdgeTestCase):
    def test_listing_unauthenticated(self):
        response = self.client.get("/api/edges/")
        self.assertIn(response.status_code, (401, 403))

    def test_listing_owned_node_only(self):
        user = self._create_user("owner-a")
        self._register_node_as(user, "node-a", name="A's Node", zone_id="zone-1")
        token = self._access_token(user)
        response = self.client.get(
            "/api/edges/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["node_id"], "node-a")
        self.assertEqual(response.data[0]["owner"], "owner-a")
        # No credential material in the listing.
        self.assertNotIn("api_key", response.data[0])
        self.assertNotIn("api_key_hash", response.data[0])

    def test_listing_excludes_other_users_nodes(self):
        user_a = self._create_user("owner-a")
        user_b = self._create_user("owner-b")
        self._register_node_as(user_a, "node-a", name="A's Node", zone_id="zone-1")

        token = self._access_token(user_b)
        response = self.client.get(
            "/api/edges/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_listing_superuser_sees_all(self):
        user_a = self._create_user("owner-a")
        self._register_node_as(user_a, "node-a", name="A's Node", zone_id="zone-1")
        self._register_node("node-unowned", name="Unowned", zone_id="zone-2")

        admin = self._create_superuser()
        token = self._access_token(admin)
        response = self.client.get(
            "/api/edges/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        node_ids = {item["node_id"] for item in response.data}
        self.assertEqual(node_ids, {"node-a", "node-unowned"})


@override_settings(
    EDGE_PROVISIONING_TOKEN=PROVISIONING_TOKEN,
    EDGE_ALLOWED_ZONES=ALLOWED_ZONES,
)
class SensorIngestionTests(EdgeTestCase):
    PAYLOAD = {
        "temperature": 21.5,
        "humidity": 55.0,
        "soil_moisture": 40.0,
        "light": 720,
    }

    def test_legacy_request_still_works(self):
        response = self.client.post("/api/sensors/", self.PAYLOAD, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data.get("node_id"))
        self.assertIsNone(response.data.get("zone_id"))

    def test_reading_from_node_has_node_and_zone(self):
        api_key = self._register_node("node-src", zone_id="zone-2")
        response = self.client.post(
            "/api/sensors/", self.PAYLOAD, format="json", HTTP_X_EDGE_KEY=api_key
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["node_id"], "node-src")
        self.assertEqual(response.data["zone_id"], "zone-2")

        node = EdgeNode.objects.get(node_id="node-src")
        self.assertIsNotNone(node.last_data_at)

    def test_node_cannot_impersonate_another_node(self):
        self._register_node("node-a", zone_id="zone-1")
        api_key_b = self._register_node("node-b", zone_id="zone-2")

        payload = dict(self.PAYLOAD, node_id="node-a", zone_id="zone-1")
        response = self.client.post(
            "/api/sensors/", payload, format="json", HTTP_X_EDGE_KEY=api_key_b
        )
        self.assertEqual(response.status_code, 201)
        # Source is derived from the key, not the client-supplied values.
        self.assertEqual(response.data["node_id"], "node-b")
        self.assertEqual(response.data["zone_id"], "zone-2")

    def test_unknown_key_rejected(self):
        response = self.client.post(
            "/api/sensors/", self.PAYLOAD, format="json", HTTP_X_EDGE_KEY="bogus"
        )
        self.assertEqual(response.status_code, 401)

    def test_disabled_node_rejected(self):
        api_key = self._register_node("node-off")
        node = EdgeNode.objects.get(node_id="node-off")
        node.status = EdgeNode.Status.DISABLED
        node.save()

        response = self.client.post(
            "/api/sensors/", self.PAYLOAD, format="json", HTTP_X_EDGE_KEY=api_key
        )
        self.assertEqual(response.status_code, 401)

    def test_last_data_at_only_after_success(self):
        api_key = self._register_node("node-fail")
        node = EdgeNode.objects.get(node_id="node-fail")

        response = self.client.post(
            "/api/sensors/",
            {"temperature": "not-a-number"},
            format="json",
            HTTP_X_EDGE_KEY=api_key,
        )
        self.assertEqual(response.status_code, 400)
        node.refresh_from_db()
        self.assertIsNone(node.last_data_at)

    def test_existing_sensor_endpoints_still_work(self):
        # A legacy reading (node_id=None) is visible only to a superuser.
        admin = self._create_superuser()
        auth = {"HTTP_AUTHORIZATION": f"Bearer {self._access_token(admin)}"}

        create = self.client.post("/api/sensors/", self.PAYLOAD, format="json")
        self.assertEqual(create.status_code, 201)
        reading_id = create.data["id"]

        listing = self.client.get("/api/sensors/", **auth)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)

        single = self.client.get(f"/api/sensors/{reading_id}/", **auth)
        self.assertEqual(single.status_code, 200)
        self.assertEqual(single.data["id"], reading_id)

        history = self.client.get("/api/sensors/history/24h/", **auth)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.data), 1)

        deleted = self.client.delete(f"/api/sensors/del/{reading_id}/", **auth)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(SensorReading.objects.count(), 0)


@override_settings(
    EDGE_PROVISIONING_TOKEN=PROVISIONING_TOKEN,
    EDGE_ALLOWED_ZONES=ALLOWED_ZONES,
)
class OwnershipIsolationTests(EdgeTestCase):
    def test_sensor_read_requires_auth(self):
        response = self.client.get("/api/sensors/")
        self.assertEqual(response.status_code, 401)

    def test_user_cannot_read_other_users_reading(self):
        user_a = self._create_user("owner-a")
        user_b = self._create_user("owner-b")
        api_key_a = self._register_node_as(user_a, "node-a")
        reading = self._create_reading(api_key=api_key_a)

        token = self._access_token(user_b)
        response = self.client.get(
            f"/api/sensors/{reading['id']}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # 404 (not 403) so we do not leak that the reading exists.
        self.assertEqual(response.status_code, 404)

    def test_user_list_excludes_other_users_readings(self):
        user_a = self._create_user("owner-a")
        user_b = self._create_user("owner-b")
        api_key_a = self._register_node_as(user_a, "node-a")
        self._create_reading(api_key=api_key_a)

        token = self._access_token(user_b)
        response = self.client.get(
            "/api/sensors/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_user_history_excludes_other_users_readings(self):
        user_a = self._create_user("owner-a")
        user_b = self._create_user("owner-b")
        api_key_a = self._register_node_as(user_a, "node-a")
        self._create_reading(api_key=api_key_a)

        token = self._access_token(user_b)
        response = self.client.get(
            "/api/sensors/history/24h/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_user_cannot_delete_other_users_reading(self):
        user_a = self._create_user("owner-a")
        user_b = self._create_user("owner-b")
        api_key_a = self._register_node_as(user_a, "node-a")
        reading = self._create_reading(api_key=api_key_a)

        token = self._access_token(user_b)
        response = self.client.delete(
            f"/api/sensors/del/{reading['id']}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SensorReading.objects.filter(pk=reading["id"]).exists())

    def test_legacy_reading_invisible_to_non_superuser(self):
        self._create_reading()  # node_id=None

        user = self._create_user("regular")
        token = self._access_token(user)

        listing = self.client.get(
            "/api/sensors/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data, [])

    def test_superuser_sees_legacy_and_owned(self):
        user_a = self._create_user("owner-a")
        api_key_a = self._register_node_as(user_a, "node-a")
        self._create_reading(api_key=api_key_a)
        self._create_reading()  # legacy, node_id=None

        admin = self._create_superuser()
        token = self._access_token(admin)
        response = self.client.get(
            "/api/sensors/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_owner_can_read_and_delete_own_reading(self):
        user = self._create_user("owner-a")
        api_key = self._register_node_as(user, "node-a")
        reading = self._create_reading(api_key=api_key)
        token = self._access_token(user)

        single = self.client.get(
            f"/api/sensors/{reading['id']}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(single.status_code, 200)
        self.assertEqual(single.data["id"], reading["id"])

        deleted = self.client.delete(
            f"/api/sensors/del/{reading['id']}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(deleted.status_code, 200)


@override_settings(
    EDGE_PROVISIONING_TOKEN=PROVISIONING_TOKEN,
    EDGE_ALLOWED_ZONES=ALLOWED_ZONES,
    EDGE_HEARTBEAT_TIMEOUT=60,
)
class EdgeHealthCheckTests(EdgeTestCase):
    def _make_node(self, node_id, status, last_heartbeat):
        api_key = self._register_node(node_id)
        node = EdgeNode.objects.get(node_id=node_id)
        node.status = status
        node.last_heartbeat = last_heartbeat
        node.save()
        return node

    def test_recent_heartbeat_stays_online(self):
        node = self._make_node(
            "node-fresh", EdgeNode.Status.ONLINE, timezone.now()
        )
        call_command("check_edge_health")
        node.refresh_from_db()
        self.assertEqual(node.status, EdgeNode.Status.ONLINE)

    def test_stale_heartbeat_becomes_offline(self):
        node = self._make_node(
            "node-stale",
            EdgeNode.Status.ONLINE,
            timezone.now() - timedelta(seconds=120),
        )
        call_command("check_edge_health")
        node.refresh_from_db()
        self.assertEqual(node.status, EdgeNode.Status.OFFLINE)

    def test_missing_heartbeat_becomes_offline(self):
        node = self._make_node("node-missing", EdgeNode.Status.ONLINE, None)
        call_command("check_edge_health")
        node.refresh_from_db()
        self.assertEqual(node.status, EdgeNode.Status.OFFLINE)

    def test_disabled_node_stays_disabled(self):
        node = self._make_node("node-disabled", EdgeNode.Status.DISABLED, None)
        call_command("check_edge_health")
        node.refresh_from_db()
        self.assertEqual(node.status, EdgeNode.Status.DISABLED)

    def test_rerun_is_idempotent(self):
        node = self._make_node(
            "node-idem",
            EdgeNode.Status.ONLINE,
            timezone.now() - timedelta(seconds=120),
        )
        call_command("check_edge_health")
        call_command("check_edge_health")
        node.refresh_from_db()
        self.assertEqual(node.status, EdgeNode.Status.OFFLINE)


class RegressionTests(EdgeTestCase):
    def test_jwt_login_still_works(self):
        self._create_user(username="loginuser", password="secret-pass-123")
        response = self.client.post(
            "/api/users/login/",
            {"username": "loginuser", "password": "secret-pass-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_llm_modules_import(self):
        # Ensure the LLM app remains importable after the changes.
        from llm import serializers, services, views  # noqa: F401
