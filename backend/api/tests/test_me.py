from rest_framework.test import APITestCase

from tenants.models import Tenant
from users.models import User

class MeEndpointTest(APITestCase):
    def setUp(self):
        # Create a tenant
        self.tenant = Tenant.objects.create(
            name="Test University",
            slug="test-university",
        )

        # Create a user belonging to that tenant
        self.user = User.objects.create_user(
            email="student@test.com",
            password="password123",
            tenant=self.tenant,
        )

    def test_me_endpoint_returns_user_data(self):
        # Log the user in
        self.client.login(email="student@test.com", password="password123")

        # Call the API
        response = self.client.get("/api/v1/me/")

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "student@test.com")
        self.assertEqual(response.data["tenant"], "Test University")
