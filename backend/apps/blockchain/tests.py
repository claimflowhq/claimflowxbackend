from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import UserRole
from apps.blockchain.models import TransactionRecord, TransactionType, TransactionStatus
from apps.blockchain.soroban_client import soroban_service

User = get_user_model()

class BlockchainTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="analyst",
            email="analyst@example.com",
            password="Password123!",
            role=UserRole.REVIEWER
        )
        self.client.force_authenticate(user=self.user)

    def test_contract_info_endpoint(self):
        res = self.client.get("/api/v1/blockchain/contract-info/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("contract_id", res.data)
        self.assertIn("network", res.data)
        self.assertEqual(res.data['network'], "TESTNET")
        self.assertEqual(res.data['status'], "OPERATIONAL")

    def test_transaction_listing_and_verification(self):
        tx = TransactionRecord.objects.create(
            claim_reference="CLM-20261116-TEST01",
            tx_hash="0xabcd1234ef567890aabbccddeeff00112233445566778899aabbccddeeff0011",
            tx_type=TransactionType.CLAIM_REGISTRATION,
            status=TransactionStatus.SUCCESSFUL,
            network="STELLAR_TESTNET",
            contract_id="CCLAIMFLOWTEST01",
            ledger_sequence=5201234,
            explorer_url="https://stellar.expert/explorer/testnet/tx/0xabcd1234",
            raw_response={"status": "Submitted"}
        )

        # List transactions
        res_list = self.client.get("/api/v1/blockchain/transactions/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['count'], 1)

        # Verify transaction
        res_verify = self.client.get(f"/api/v1/blockchain/transactions/{tx.tx_hash}/")
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        self.assertEqual(res_verify.data['claim_reference'], "CLM-20261116-TEST01")

    def test_claim_on_chain_state_query(self):
        # Register a claim in SorobanService
        soroban_service.register_claim(
            claim_id="CLM-ONCHAIN-99",
            claimant_address="GBU2DCSH5QSKUGW7USN4QL7I72O5ZPGX7Z44FUX3F47V4K633F2G245C",
            policy_id="POL-HEALTH-101",
            requested_amount=500
        )

        res = self.client.get("/api/v1/blockchain/claims/CLM-ONCHAIN-99/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['claim_id'], "CLM-ONCHAIN-99")
        self.assertEqual(res.data['status'], "Submitted")

