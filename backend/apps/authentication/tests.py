from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import UserRole

User = get_user_model()

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_user_registration_success(self):
        data = {
            "username": "claimant1",
            "email": "claimant1@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "role": UserRole.CLAIMANT,
            "wallet_address": "GBU2DCSH5QSKUGW7USN4QL7I72O5ZPGX7Z44FUX3F47V4K633F2G245C"
        }
        res = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['username'], "claimant1")
        self.assertEqual(res.data['role'], UserRole.CLAIMANT)

    def test_user_registration_password_mismatch(self):
        data = {
            "username": "claimant2",
            "email": "claimant2@example.com",
            "password": "Password123!",
            "password_confirm": "MismatchPass123!",
            "role": UserRole.CLAIMANT
        }
        res = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res.data)

    def test_user_login_jwt(self):
        User.objects.create_user(
            username="reviewer1",
            email="reviewer1@example.com",
            password="ReviewerPassword123!",
            role=UserRole.REVIEWER
        )
        login_data = {
            "username": "reviewer1",
            "password": "ReviewerPassword123!"
        }
        res = self.client.post("/api/v1/auth/login/", login_data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data['user']['role'], UserRole.REVIEWER)

    def test_user_profile_me_authenticated(self):
        user = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password="AdminPassword123!",
            role=UserRole.ADMIN
        )
        self.client.force_authenticate(user=user)
        res = self.client.get("/api/v1/auth/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], "admin1")
        self.assertEqual(res.data['role'], UserRole.ADMIN)

