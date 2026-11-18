from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import UserRole
from apps.policies.models import Policy, PolicyCategory
from apps.claims.models import Claim, ClaimStatus, PayoutAuthorization
from apps.claims.services import ClaimService
from apps.claims.tasks import sync_claim_to_soroban_task, sync_payout_to_soroban_task

User = get_user_model()

class ClaimLifecycleAndAuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.claimant = User.objects.create_user(
            username="john_claimant",
            email="john@example.com",
            password="Password123!",
            role=UserRole.CLAIMANT,
            wallet_address="GBU2DCSH5QSKUGW7USN4QL7I72O5ZPGX7Z44FUX3F47V4K633F2G245C"
        )
        self.unauthorized_claimant = User.objects.create_user(
            username="eve_intruder",
            email="eve@example.com",
            password="Password123!",
            role=UserRole.CLAIMANT
        )
        self.reviewer = User.objects.create_user(
            username="sarah_reviewer",
            email="sarah@example.com",
            password="Password123!",
            role=UserRole.REVIEWER,
            wallet_address="GCREVIEWER000000000000000000000000000000000000000000000000"
        )
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@claimflow.io",
            password="Password123!",
            role=UserRole.ADMIN
        )

        # Policy
        self.policy = Policy.objects.create(
            policy_number="POL-AUTO-7788",
            policyholder=self.claimant,
            category=PolicyCategory.AUTO,
            coverage_limit=Decimal('5000.00'),
            deductible=Decimal('250.00'),
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_active=True
        )

    def test_01_claim_submission_success(self):
        self.client.force_authenticate(user=self.claimant)
        data = {
            "policy": self.policy.id,
            "category": "AUTO",
            "incident_description": "Rear bumper collision at parking lot.",
            "incident_date": "2026-11-10",
            "requested_amount": "800.00",
            "evidence": [
                {
                    "file_name": "bumper_photo.jpg",
                    "file_url": "https://storage.claimflow.io/bumper.jpg",
                    "document_type": "PHOTO",
                    "file_size_bytes": 1048576
                }
            ]
        }
        res = self.client.post("/api/v1/claims/", data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['claim_reference'].startswith("CLM-"))
        self.assertEqual(res.data['status'], ClaimStatus.SUBMITTED)
        self.assertIsNotNone(res.data['on_chain_tx_hash'])
        self.assertEqual(len(res.data['evidence']), 1)

    def test_02_claim_submission_exceeds_coverage_limit_fails(self):
        self.client.force_authenticate(user=self.claimant)
        data = {
            "policy": self.policy.id,
            "category": "AUTO",
            "incident_description": "Claim exceeding coverage limit.",
            "incident_date": "2026-11-10",
            "requested_amount": "10000.00" # limit is 5000
        }
        res = self.client.post("/api/v1/claims/", data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("requested_amount", str(res.data))

    def test_03_claim_submission_zero_or_negative_amount_fails(self):
        self.client.force_authenticate(user=self.claimant)
        data = {
            "policy": self.policy.id,
            "category": "AUTO",
            "incident_description": "Invalid amount claim.",
            "incident_date": "2026-11-10",
            "requested_amount": "0.00"
        }
        res = self.client.post("/api/v1/claims/", data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_04_reviewer_workflow_review_approve(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Valid damage report.",
            incident_date="2026-11-12",
            requested_amount=Decimal('1200.00')
        )

        # 1. Move to review
        self.client.force_authenticate(user=self.reviewer)
        res_review = self.client.post(f"/api/v1/claims/{claim.id}/review/")
        self.assertEqual(res_review.status_code, status.HTTP_200_OK)
        self.assertEqual(res_review.data['status'], ClaimStatus.UNDER_REVIEW)

        # 2. Approve claim
        approve_data = {
            "approved_amount": "1000.00",
            "notes": "Damage verified with official repair estimate."
        }
        res_approve = self.client.post(f"/api/v1/claims/{claim.id}/approve/", approve_data)
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        self.assertEqual(res_approve.data['status'], ClaimStatus.APPROVED)
        self.assertEqual(Decimal(res_approve.data['approved_amount']), Decimal('1000.00'))

    def test_05_unauthorized_user_cannot_approve(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Test incident",
            incident_date="2026-11-12",
            requested_amount=Decimal('600.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)

        # Claimant attempts to approve their own or someone's claim
        self.client.force_authenticate(user=self.claimant)
        res = self.client.post(f"/api/v1/claims/{claim.id}/approve/", {
            "approved_amount": "600.00",
            "notes": "Attempting self-approval"
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_06_reviewer_workflow_reject(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Uncovered incident damage.",
            incident_date="2026-11-12",
            requested_amount=Decimal('500.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)

        self.client.force_authenticate(user=self.reviewer)
        reject_data = {"notes": "Incident occurred outside coverage period."}
        res_reject = self.client.post(f"/api/v1/claims/{claim.id}/reject/", reject_data)
        self.assertEqual(res_reject.status_code, status.HTTP_200_OK)
        self.assertEqual(res_reject.data['status'], ClaimStatus.REJECTED)

    def test_07_cannot_approve_already_rejected_claim(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Rejected claim.",
            incident_date="2026-11-12",
            requested_amount=Decimal('500.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)
        ClaimService.reject_claim(claim, self.reviewer, "Rejected reason")

        self.client.force_authenticate(user=self.reviewer)
        res = self.client.post(f"/api/v1/claims/{claim.id}/approve/", {
            "approved_amount": "400.00",
            "notes": "Trying to approve after rejection"
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_08_payout_authorization_success(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Approved claim for payout.",
            incident_date="2026-11-12",
            requested_amount=Decimal('1500.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)
        ClaimService.approve_claim(claim, self.reviewer, Decimal('1200.00'), "Approved")

        self.client.force_authenticate(user=self.reviewer)
        payout_data = {"payout_amount": "1200.00"}
        res = self.client.post(f"/api/v1/claims/{claim.id}/authorize_payout/", payout_data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'CONFIRMED')
        self.assertEqual(Decimal(res.data['amount']), Decimal('1200.00'))

        # Verify claim status updated
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.PAYOUT_AUTHORIZED)
        self.assertEqual(claim.authorized_payout_amount, Decimal('1200.00'))

    def test_09_payout_exceeding_approved_amount_fails(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Approved claim.",
            incident_date="2026-11-12",
            requested_amount=Decimal('1000.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)
        ClaimService.approve_claim(claim, self.reviewer, Decimal('800.00'), "Approved for 800")

        self.client.force_authenticate(user=self.reviewer)
        # Attempting to authorize 900 when approved was 800
        res = self.client.post(f"/api/v1/claims/{claim.id}/authorize_payout/", {"payout_amount": "900.00"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_10_payout_authorization_for_rejected_claim_fails(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Rejected claim.",
            incident_date="2026-11-12",
            requested_amount=Decimal('500.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)
        ClaimService.reject_claim(claim, self.reviewer, "Rejected")

        self.client.force_authenticate(user=self.reviewer)
        res = self.client.post(f"/api/v1/claims/{claim.id}/authorize_payout/", {"payout_amount": "500.00"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_11_duplicate_payout_authorization_prevented(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Claim with payout.",
            incident_date="2026-11-12",
            requested_amount=Decimal('1000.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)
        ClaimService.approve_claim(claim, self.reviewer, Decimal('1000.00'), "Approved")
        ClaimService.authorize_payout(claim, self.reviewer, Decimal('1000.00'))

        self.client.force_authenticate(user=self.reviewer)
        # Duplicate authorization attempt
        res = self.client.post(f"/api/v1/claims/{claim.id}/authorize_payout/", {"payout_amount": "1000.00"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_12_settlement_workflow(self):
        claim = ClaimService.create_claim(
            claimant=self.claimant,
            policy=self.policy,
            category="AUTO",
            incident_description="Claim settling.",
            incident_date="2026-11-12",
            requested_amount=Decimal('750.00')
        )
        ClaimService.move_to_review(claim, self.reviewer)
        ClaimService.approve_claim(claim, self.reviewer, Decimal('750.00'), "Approved")
        ClaimService.authorize_payout(claim, self.reviewer, Decimal('750.00'))

        self.client.force_authenticate(user=self.admin)
        settle_data = {
            "settlement_reference": "tx_stellar_testnet_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
        res = self.client.post(f"/api/v1/claims/{claim.id}/settle/", settle_data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], ClaimStatus.SETTLED)

        # Confirm timeline recorded settlement
        res_timeline = self.client.get(f"/api/v1/claims/{claim.id}/timeline/")
        self.assertEqual(res_timeline.status_code, status.HTTP_200_OK)
        actions = [e['action'] for e in res_timeline.data]
        self.assertIn("CLAIM_SETTLED", actions)

    def test_13_dashboard_metrics(self):
        # Create multiple claims across statuses
        c1 = ClaimService.create_claim(self.claimant, self.policy, "AUTO", "Inc 1", "2026-11-10", Decimal('500.00'))
        c2 = ClaimService.create_claim(self.claimant, self.policy, "AUTO", "Inc 2", "2026-11-10", Decimal('800.00'))
        ClaimService.move_to_review(c2, self.reviewer)
        ClaimService.approve_claim(c2, self.reviewer, Decimal('700.00'), "Approved")
        ClaimService.authorize_payout(c2, self.reviewer, Decimal('700.00'))

        self.client.force_authenticate(user=self.reviewer)
        res = self.client.get("/api/v1/claims/dashboard/metrics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res.data['total_claims'], 2)
        self.assertGreaterEqual(Decimal(res.data['total_requested_volume']), Decimal('1300.00'))
        self.assertGreaterEqual(Decimal(res.data['total_authorized_payout_volume']), Decimal('700.00'))

    def test_14_celery_tasks(self):
        claim = ClaimService.create_claim(self.claimant, self.policy, "AUTO", "Inc Task", "2026-11-10", Decimal('400.00'))
        res_claim_task = sync_claim_to_soroban_task(claim.id)
        self.assertEqual(res_claim_task['status'], "SUCCESS")

        ClaimService.move_to_review(claim, self.reviewer)
        ClaimService.approve_claim(claim, self.reviewer, Decimal('400.00'), "Approve")
        payout = ClaimService.authorize_payout(claim, self.reviewer, Decimal('400.00'))

        res_payout_task = sync_payout_to_soroban_task(payout.id)
        self.assertEqual(res_payout_task['status'], "SUCCESS")

