import uuid
from django.db import models
from django.conf import settings
from apps.policies.models import Policy

class ClaimStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    PAYOUT_AUTHORIZED = 'PAYOUT_AUTHORIZED', 'Payout Authorized'
    SETTLED = 'SETTLED', 'Settled'

class ClaimCategory(models.TextChoices):
    HEALTH = 'HEALTH', 'Health Insurance'
    AUTO = 'AUTO', 'Automobile Insurance'
    PROPERTY = 'PROPERTY', 'Property & Casualty'
    LIFE = 'LIFE', 'Life Insurance'
    TRAVEL = 'TRAVEL', 'Travel Insurance'

class OnChainSyncStatus(models.TextChoices):
    NOT_SUBMITTED = 'NOT_SUBMITTED', 'Not Submitted'
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    FAILED = 'FAILED', 'Failed'

def generate_claim_reference():
    """Generates unique claim reference: CLM-YYYYMMDD-XXXXXXXX"""
    import datetime
    today = datetime.date.today().strftime('%Y%m%d')
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"CLM-{today}-{unique_suffix}"

class Claim(models.Model):
    claim_reference = models.CharField(
        max_length=64,
        unique=True,
        default=generate_claim_reference,
        db_index=True,
        help_text="Unique verifiable reference for claim"
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name='claims'
    )
    category = models.CharField(
        max_length=32,
        choices=ClaimCategory.choices,
        default=ClaimCategory.HEALTH
    )
    incident_description = models.TextField()
    incident_date = models.DateField()
    requested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Requested compensation amount in USDC equivalent"
    )
    approved_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Approved compensation amount determined by reviewer"
    )
    authorized_payout_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Payout amount authorized on Soroban smart contract"
    )
    status = models.CharField(
        max_length=32,
        choices=ClaimStatus.choices,
        default=ClaimStatus.SUBMITTED,
        db_index=True
    )
    assigned_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_claims'
    )
    on_chain_status = models.CharField(
        max_length=32,
        choices=OnChainSyncStatus.choices,
        default=OnChainSyncStatus.CONFIRMED
    )
    on_chain_tx_hash = models.CharField(max_length=96, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.claim_reference} - {self.claimant.username} [{self.status}]"

class SupportingEvidence(models.Model):
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='evidence'
    )
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=512)
    document_type = models.CharField(
        max_length=64,
        default='SUPPORTING_DOCUMENT',
        help_text="e.g. MEDICAL_BILL, POLICE_REPORT, REPAIR_ESTIMATE, PHOTO"
    )
    file_size_bytes = models.BigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.claim.claim_reference}: {self.file_name}"

class ClaimReviewDecision(models.Model):
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='review_decisions'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    decision = models.CharField(
        max_length=32,
        choices=[
            ('UNDER_REVIEW', 'Under Review'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ]
    )
    approved_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )
    notes = models.TextField()
    tx_hash = models.CharField(max_length=96, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.claim.claim_reference} - {self.decision} by {self.reviewer.username}"

class PayoutAuthorization(models.Model):
    claim = models.OneToOneField(
        Claim,
        on_delete=models.CASCADE,
        related_name='payout_authorization'
    )
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payout_authorizations'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=32,
        choices=[
            ('PENDING', 'Pending'),
            ('CONFIRMED', 'Confirmed'),
            ('FAILED', 'Failed'),
        ],
        default='CONFIRMED'
    )
    tx_hash = models.CharField(max_length=96, null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    settlement_reference = models.CharField(max_length=128, blank=True, default='')
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payout Auth: {self.claim.claim_reference} - {self.amount} USDC [{self.status}]"

class ClaimTimelineEvent(models.Model):
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='timeline'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=64)
    from_status = models.CharField(max_length=32, blank=True, default='')
    to_status = models.CharField(max_length=32, blank=True, default='')
    details = models.TextField(blank=True, default='')
    tx_hash = models.CharField(max_length=96, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.claim.claim_reference} - {self.action} ({self.timestamp})"

