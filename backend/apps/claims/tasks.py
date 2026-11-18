import logging
from celery import shared_task
from .models import Claim, PayoutAuthorization
from apps.blockchain.soroban_client import soroban_service

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def sync_claim_to_soroban_task(self, claim_id: int):
    """Celery task to register a submitted claim on Soroban smart contract."""
    try:
        claim = Claim.objects.get(id=claim_id)
        tx = soroban_service.register_claim(
            claim_id=claim.claim_reference,
            claimant_address=claim.claimant.wallet_address or "",
            policy_id=claim.policy.policy_number,
            requested_amount=claim.requested_amount
        )
        claim.on_chain_tx_hash = tx.tx_hash
        claim.save(update_fields=['on_chain_tx_hash'])
        return {"status": "SUCCESS", "tx_hash": tx.tx_hash}
    except Exception as exc:
        logger.error(f"Error syncing claim {claim_id} to Soroban: {exc}")
        raise self.retry(exc=exc, countdown=10)

@shared_task(bind=True, max_retries=3)
def sync_payout_to_soroban_task(self, payout_id: int):
    """Celery task to record payout authorization on Soroban."""
    try:
        payout = PayoutAuthorization.objects.get(id=payout_id)
        tx = soroban_service.authorize_payout(
            claim_id=payout.claim.claim_reference,
            caller_address=payout.authorized_by.wallet_address or "",
            payout_amount=payout.amount
        )
        payout.tx_hash = tx.tx_hash
        payout.status = 'CONFIRMED'
        payout.save(update_fields=['tx_hash', 'status'])
        return {"status": "SUCCESS", "tx_hash": tx.tx_hash}
    except Exception as exc:
        logger.error(f"Error syncing payout {payout_id} to Soroban: {exc}")
        raise self.retry(exc=exc, countdown=10)

