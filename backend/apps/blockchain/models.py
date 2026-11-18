from django.db import models

class TransactionType(models.TextChoices):
    CLAIM_REGISTRATION = 'CLAIM_REGISTRATION', 'Claim Registration'
    REVIEW_ASSIGNMENT = 'REVIEW_ASSIGNMENT', 'Review Assignment'
    CLAIM_APPROVAL = 'CLAIM_APPROVAL', 'Claim Approval'
    CLAIM_REJECTION = 'CLAIM_REJECTION', 'Claim Rejection'
    PAYOUT_AUTHORIZATION = 'PAYOUT_AUTHORIZATION', 'Payout Authorization'
    SETTLEMENT = 'SETTLEMENT', 'Settlement'

class TransactionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SUCCESSFUL = 'SUCCESSFUL', 'Successful'
    FAILED = 'FAILED', 'Failed'

class TransactionRecord(models.Model):
    claim_reference = models.CharField(max_length=64, db_index=True)
    tx_hash = models.CharField(max_length=96, unique=True, db_index=True)
    tx_type = models.CharField(max_length=32, choices=TransactionType.choices)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.SUCCESSFUL
    )
    network = models.CharField(max_length=32, default='STELLAR_TESTNET')
    contract_id = models.CharField(max_length=96)
    ledger_sequence = models.BigIntegerField(null=True, blank=True)
    explorer_url = models.URLField(max_length=255)
    error_message = models.TextField(blank=True, default='')
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tx_type} [{self.status}] - {self.claim_reference} ({self.tx_hash[:16]}...)"

