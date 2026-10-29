from django.contrib.auth import get_user_model
from rest_framework.test import APITransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class MeViewTests(APITransactionTestCase):
    def _create_user(self, username="tester", password="secret-pass-123"):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=password,
        )

    def _access_token(self, user):
        return str(RefreshToken.for_user(user).access_token)

    def test_me_requires_auth(self):
        response = self.client.get("/api/users/me/")
        self.assertIn(response.status_code, (401, 403))

    def test_me_returns_profile(self):
        user = self._create_user("alice")
        token = self._access_token(user)
        response = self.client.get(
            "/api/users/me/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "alice")
        self.assertEqual(response.data["email"], "alice@example.com")
