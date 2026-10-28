from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.test import APITransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import EdgeNode

User = get_user_model()


class LLMAuthTests(APITransactionTestCase):
    def _create_user(self, username="tester", password="secret-pass-123"):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=password,
        )

    def _access_token(self, user):
        return str(RefreshToken.for_user(user).access_token)

    def test_recommend_requires_auth(self):
        response = self.client.post(
            "/api/llm/recommend/", {"hours": 24}, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_chat_requires_auth(self):
        response = self.client.post(
            "/api/llm/chat/", {"message": "hi"}, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def _mock_context(self):
        return {
            "recommendation": "ok",
            "context": {
                "latest_reading": None,
                "history_hours": 24,
                "historical_readings": [],
            },
        }

    def test_recommend_scoped_to_owned_nodes(self):
        user = self._create_user("owner-a")
        EdgeNode.objects.create(
            node_id="node-a",
            name="Node A",
            zone_id="zone-1",
            api_key_hash="deadbeef",
            owner=user,
        )
        token = self._access_token(user)

        with mock.patch("llm.views.generate_recommendation") as service:
            service.return_value = self._mock_context()
            response = self.client.post(
                "/api/llm/recommend/",
                {"hours": 24, "language": "en"},
                format="json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        service.assert_called_once()
        self.assertEqual(service.call_args.kwargs["node_ids"], ["node-a"])

    def test_recommend_scoped_to_empty_for_user_without_nodes(self):
        user = self._create_user("owner-none")
        token = self._access_token(user)

        with mock.patch("llm.views.generate_recommendation") as service:
            service.return_value = self._mock_context()
            response = self.client.post(
                "/api/llm/recommend/",
                {"hours": 24, "language": "en"},
                format="json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        service.assert_called_once()
        self.assertEqual(service.call_args.kwargs["node_ids"], [])
