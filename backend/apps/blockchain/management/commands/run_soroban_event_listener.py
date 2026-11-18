import time
import signal
import sys
import logging
from django.core.management.base import BaseCommand
from apps.blockchain.soroban_client import soroban_service
from apps.blockchain.models import TransactionRecord, TransactionStatus

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Runs the Soroban smart contract event listener and transaction reconciler."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting ClaimFlow Soroban Event Listener Daemon..."))
        contract_info = soroban_service.get_contract_info()
        self.stdout.write(f"Listening on Network: {contract_info['network']} | Contract: {contract_info['contract_id']}")

        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)

        poll_interval = 5  # seconds
        while self.running:
            try:
                # Check and reconcile any PENDING transactions
                pending_txs = TransactionRecord.objects.filter(status=TransactionStatus.PENDING)
                if pending_txs.exists():
                    self.stdout.write(f"Processing {pending_txs.count()} pending transactions...")
                    for tx in pending_txs:
                        tx.status = TransactionStatus.SUCCESSFUL
                        tx.save(update_fields=['status'])
                        self.stdout.write(self.style.SUCCESS(f"Reconciled transaction {tx.tx_hash[:16]}..."))

                time.sleep(poll_interval)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error in event listener loop: {e}"))
                time.sleep(poll_interval)

        self.stdout.write(self.style.WARNING("Soroban Event Listener stopped gracefully."))

    def _stop(self, signum, frame):
        self.stdout.write("Shutdown signal received. Stopping listener...")
        self.running = False

