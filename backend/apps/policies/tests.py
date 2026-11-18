from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import UserRole
from apps.policies.models import Policy, PolicyCategory

User = get_user_model()

class PolicyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.claimant = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Password123!",
            role=UserRole.CLAIMANT
        )
        self.reviewer = User.objects.create_user(
            username="bob_reviewer",
            email="bob@example.com",
            password="Password123!",
            role=UserRole.REVIEWER
        )
        self.policy = Policy.objects.create(
            policy_number="POL-HEALTH-101",
            policyholder=self.claimant,
            category=PolicyCategory.HEALTH,
            coverage_limit=10000.00,
            deductible=250.00,
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_active=True
        )

    def test_claimant_sees_own_policy(self):
        self.client.force_authenticate(user=self.claimant)
        res = self.client.get("/api/v1/policies/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['policy_number'], "POL-HEALTH-101")

    def test_reviewer_can_create_policy(self):
        self.client.force_authenticate(user=self.reviewer)
        data = {
            "policy_number": "POL-AUTO-202",
            "policyholder": self.claimant.id,
            "category": PolicyCategory.AUTO,
            "coverage_limit": "25000.00",
            "deductible": "500.00",
            "start_date": "2026-02-01",
            "end_date": "2027-02-01",
            "is_active": True
        }
        res = self.client.post("/api/v1/policies/", data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Policy.objects.count(), 2)

    def test_claimant_cannot_create_policy(self):
        self.client.force_authenticate(user=self.claimant)
        data = {
            "policy_number": "POL-UNAUTH-303",
            "category": PolicyCategory.TRAVEL,
            "coverage_limit": "5000.00",
            "deductible": "0.00",
            "start_date": "2026-03-01",
            "end_date": "2026-04-01",
            "is_active": True
        }
        res = self.client.post("/api/v1/policies/", data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

