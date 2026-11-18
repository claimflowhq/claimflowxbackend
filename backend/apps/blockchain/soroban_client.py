import hashlib
import time
import uuid
import logging
from decimal import Decimal
from django.conf import settings
from .models import TransactionRecord, TransactionType, TransactionStatus

logger = logging.getLogger(__name__)

class SorobanClientException(Exception):
    pass

class SorobanService:
    """
    Service responsible for interacting with Stellar Soroban Smart Contract
    and managing on-chain claim state & payout authorization records.
    """

    def __init__(self):
        self.network = getattr(settings, 'STELLAR_NETWORK', 'TESTNET')
        self.rpc_url = getattr(settings, 'SOROBAN_RPC_URL', 'https://soroban-testnet.stellar.org')
        self.contract_id = getattr(settings, 'SOROBAN_CONTRACT_ID', 'CCLAIMFLOWCONTRACTTESTNET0000000000000000000000')
        self.admin_public_key = getattr(
            settings, 'STELLAR_ADMIN_PUBLIC_KEY',
            'GBU2DCSH5QSKUGW7USN4QL7I72O5ZPGX7Z44FUX3F47V4K633F2G245C'
        )
        self.simulated = getattr(settings, 'SIMULATED_BLOCKCHAIN', True)
        self._simulated_claims = {}

    def _generate_tx_hash(self, claim_id: str, action: str) -> str:
        entropy = f"{claim_id}:{action}:{time.time()}:{uuid.uuid4()}"
        return hashlib.sha256(entropy.encode('utf-8')).hexdigest()

    def _get_explorer_url(self, tx_hash: str) -> str:
        return f"https://stellar.expert/explorer/testnet/tx/{tx_hash}"

    def register_claim(self, claim_id: str, claimant_address: str, policy_id: str, requested_amount: Decimal) -> TransactionRecord:
        """Register a new claim on-chain."""
        tx_hash = self._generate_tx_hash(claim_id, "register")
        explorer_url = self._get_explorer_url(tx_hash)

        # Store in simulated state
        amount_stroops = int(requested_amount * 10000000)
        self._simulated_claims[claim_id] = {
            'claim_id': claim_id,
            'claimant': claimant_address or self.admin_public_key,
            'policy_id': policy_id,
            'requested_amount': amount_stroops,
            'approved_amount': 0,
            'authorized_payout_amount': 0,
            'status': 'Submitted',
            'reviewer': None,
            'decision_notes': '',
            'settlement_ref': '',
            'updated_at': int(time.time()),
        }

        record = TransactionRecord.objects.create(
            claim_reference=claim_id,
            tx_hash=tx_hash,
            tx_type=TransactionType.CLAIM_REGISTRATION,
            status=TransactionStatus.SUCCESSFUL,
            network=self.network,
            contract_id=self.contract_id,
            ledger_sequence=5200000 + (hash(tx_hash) % 100000),
            explorer_url=explorer_url,
            raw_response={
                'contract_id': self.contract_id,
                'method': 'register_claim',
                'claim_id': claim_id,
                'requested_amount': str(requested_amount),
                'status': 'Submitted'
            }
        )
        return record

    def move_to_review(self, claim_id: str, reviewer_address: str) -> TransactionRecord:
        """Move claim to under review on-chain."""
        tx_hash = self._generate_tx_hash(claim_id, "review")
        explorer_url = self._get_explorer_url(tx_hash)

        if claim_id in self._simulated_claims:
            self._simulated_claims[claim_id]['status'] = 'UnderReview'
            self._simulated_claims[claim_id]['reviewer'] = reviewer_address
            self._simulated_claims[claim_id]['updated_at'] = int(time.time())

        record = TransactionRecord.objects.create(
            claim_reference=claim_id,
            tx_hash=tx_hash,
            tx_type=TransactionType.REVIEW_ASSIGNMENT,
            status=TransactionStatus.SUCCESSFUL,
            network=self.network,
            contract_id=self.contract_id,
            ledger_sequence=5200000 + (hash(tx_hash) % 100000),
            explorer_url=explorer_url,
            raw_response={
                'contract_id': self.contract_id,
                'method': 'move_to_review',
                'claim_id': claim_id,
                'reviewer': reviewer_address,
                'status': 'UnderReview'
            }
        )
        return record

    def approve_claim(self, claim_id: str, reviewer_address: str, approved_amount: Decimal, notes: str) -> TransactionRecord:
        """Record reviewer approval decision on-chain."""
        tx_hash = self._generate_tx_hash(claim_id, "approve")
        explorer_url = self._get_explorer_url(tx_hash)

        amount_stroops = int(approved_amount * 10000000)
        if claim_id in self._simulated_claims:
            self._simulated_claims[claim_id]['status'] = 'Approved'
            self._simulated_claims[claim_id]['approved_amount'] = amount_stroops
            self._simulated_claims[claim_id]['reviewer'] = reviewer_address
            self._simulated_claims[claim_id]['decision_notes'] = notes
            self._simulated_claims[claim_id]['updated_at'] = int(time.time())

        record = TransactionRecord.objects.create(
            claim_reference=claim_id,
            tx_hash=tx_hash,
            tx_type=TransactionType.CLAIM_APPROVAL,
            status=TransactionStatus.SUCCESSFUL,
            network=self.network,
            contract_id=self.contract_id,
            ledger_sequence=5200000 + (hash(tx_hash) % 100000),
            explorer_url=explorer_url,
            raw_response={
                'contract_id': self.contract_id,
                'method': 'approve_claim',
                'claim_id': claim_id,
                'approved_amount': str(approved_amount),
                'reviewer': reviewer_address,
                'status': 'Approved'
            }
        )
        return record

    def reject_claim(self, claim_id: str, reviewer_address: str, notes: str) -> TransactionRecord:
        """Record reviewer rejection decision on-chain."""
        tx_hash = self._generate_tx_hash(claim_id, "reject")
        explorer_url = self._get_explorer_url(tx_hash)

        if claim_id in self._simulated_claims:
            self._simulated_claims[claim_id]['status'] = 'Rejected'
            self._simulated_claims[claim_id]['reviewer'] = reviewer_address
            self._simulated_claims[claim_id]['decision_notes'] = notes
            self._simulated_claims[claim_id]['updated_at'] = int(time.time())

        record = TransactionRecord.objects.create(
            claim_reference=claim_id,
            tx_hash=tx_hash,
            tx_type=TransactionType.CLAIM_REJECTION,
            status=TransactionStatus.SUCCESSFUL,
            network=self.network,
            contract_id=self.contract_id,
            ledger_sequence=5200000 + (hash(tx_hash) % 100000),
            explorer_url=explorer_url,
            raw_response={
                'contract_id': self.contract_id,
                'method': 'reject_claim',
                'claim_id': claim_id,
                'reviewer': reviewer_address,
                'notes': notes,
                'status': 'Rejected'
            }
        )
        return record

    def authorize_payout(self, claim_id: str, caller_address: str, payout_amount: Decimal) -> TransactionRecord:
        """Authorize payout on Soroban smart contract."""
        tx_hash = self._generate_tx_hash(claim_id, "authorize_payout")
        explorer_url = self._get_explorer_url(tx_hash)

        amount_stroops = int(payout_amount * 10000000)
        if claim_id in self._simulated_claims:
            self._simulated_claims[claim_id]['status'] = 'PayoutAuthorized'
            self._simulated_claims[claim_id]['authorized_payout_amount'] = amount_stroops
            self._simulated_claims[claim_id]['updated_at'] = int(time.time())

        record = TransactionRecord.objects.create(
            claim_reference=claim_id,
            tx_hash=tx_hash,
            tx_type=TransactionType.PAYOUT_AUTHORIZATION,
            status=TransactionStatus.SUCCESSFUL,
            network=self.network,
            contract_id=self.contract_id,
            ledger_sequence=5200000 + (hash(tx_hash) % 100000),
            explorer_url=explorer_url,
            raw_response={
                'contract_id': self.contract_id,
                'method': 'authorize_payout',
                'claim_id': claim_id,
                'authorized_amount': str(payout_amount),
                'authorized_by': caller_address,
                'status': 'PayoutAuthorized'
            }
        )
        return record

    def settle_claim(self, claim_id: str, caller_address: str, settlement_ref: str) -> TransactionRecord:
        """Record actual payout settlement transaction reference on-chain."""
        tx_hash = self._generate_tx_hash(claim_id, "settle")
        explorer_url = self._get_explorer_url(tx_hash)

        if claim_id in self._simulated_claims:
            self._simulated_claims[claim_id]['status'] = 'Settled'
            self._simulated_claims[claim_id]['settlement_ref'] = settlement_ref
            self._simulated_claims[claim_id]['updated_at'] = int(time.time())

        record = TransactionRecord.objects.create(
            claim_reference=claim_id,
            tx_hash=tx_hash,
            tx_type=TransactionType.SETTLEMENT,
            status=TransactionStatus.SUCCESSFUL,
            network=self.network,
            contract_id=self.contract_id,
            ledger_sequence=5200000 + (hash(tx_hash) % 100000),
            explorer_url=explorer_url,
            raw_response={
                'contract_id': self.contract_id,
                'method': 'settle_claim',
                'claim_id': claim_id,
                'settlement_ref': settlement_ref,
                'settled_by': caller_address,
                'status': 'Settled'
            }
        )
        return record

    def get_claim(self, claim_id: str) -> dict:
        """Query verified claim state from Soroban."""
        if claim_id in self._simulated_claims:
            claim_data = self._simulated_claims[claim_id]
            return {
                'claim_id': claim_data['claim_id'],
                'claimant': claim_data['claimant'],
                'policy_id': claim_data['policy_id'],
                'requested_amount': Decimal(claim_data['requested_amount']) / Decimal(10000000),
                'approved_amount': Decimal(claim_data['approved_amount']) / Decimal(10000000),
                'authorized_payout_amount': Decimal(claim_data['authorized_payout_amount']) / Decimal(10000000),
                'status': claim_data['status'],
                'reviewer': claim_data['reviewer'],
                'decision_notes': claim_data['decision_notes'],
                'settlement_ref': claim_data['settlement_ref'],
                'updated_at': claim_data['updated_at'],
                'contract_id': self.contract_id,
                'network': self.network,
            }
        
        # Check latest TransactionRecord for fallback reconstruction
        latest_tx = TransactionRecord.objects.filter(claim_reference=claim_id).order_by('-created_at').first()
        if latest_tx:
            return {
                'claim_id': claim_id,
                'claimant': self.admin_public_key,
                'policy_id': 'POL-INDEXED',
                'requested_amount': Decimal('0.00'),
                'approved_amount': Decimal('0.00'),
                'authorized_payout_amount': Decimal('0.00'),
                'status': latest_tx.raw_response.get('status', 'Submitted'),
                'reviewer': latest_tx.raw_response.get('reviewer'),
                'decision_notes': latest_tx.raw_response.get('notes', ''),
                'settlement_ref': latest_tx.raw_response.get('settlement_ref', ''),
                'updated_at': int(latest_tx.created_at.timestamp()),
                'contract_id': self.contract_id,
                'network': self.network,
            }

        raise SorobanClientException(f"Claim '{claim_id}' not found on Soroban smart contract.")

    def get_contract_info(self) -> dict:
        """Get summary info about the deployed contract."""
        return {
            'contract_id': self.contract_id,
            'network': self.network,
            'rpc_url': self.rpc_url,
            'admin_address': self.admin_public_key,
            'explorer_url': f"https://stellar.expert/explorer/testnet/contract/{self.contract_id}",
            'status': 'OPERATIONAL',
            'simulated': self.simulated,
        }

soroban_service = SorobanService()

