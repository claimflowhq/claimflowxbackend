from rest_framework import serializers
from .models import (
    Claim, SupportingEvidence, ClaimReviewDecision,
    PayoutAuthorization, ClaimTimelineEvent
)

class SupportingEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportingEvidence
        fields = ('id', 'file_name', 'file_url', 'document_type', 'file_size_bytes', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')

class ClaimTimelineEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.ReadOnlyField(source='actor.username')

    class Meta:
        model = ClaimTimelineEvent
        fields = (
            'id', 'actor', 'actor_username', 'action',
            'from_status', 'to_status', 'details', 'tx_hash', 'timestamp'
        )
        read_only_fields = fields

class ClaimReviewDecisionSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.ReadOnlyField(source='reviewer.username')

    class Meta:
        model = ClaimReviewDecision
        fields = (
            'id', 'reviewer', 'reviewer_username', 'decision',
            'approved_amount', 'notes', 'tx_hash', 'created_at'
        )
        read_only_fields = fields

class PayoutAuthorizationSerializer(serializers.ModelSerializer):
    authorized_by_username = serializers.ReadOnlyField(source='authorized_by.username')
    claim_reference = serializers.ReadOnlyField(source='claim.claim_reference')
    claimant_username = serializers.ReadOnlyField(source='claim.claimant.username')
    claimant_wallet = serializers.ReadOnlyField(source='claim.claimant.wallet_address')

    class Meta:
        model = PayoutAuthorization
        fields = (
            'id', 'claim', 'claim_reference', 'claimant_username', 'claimant_wallet',
            'authorized_by', 'authorized_by_username', 'amount', 'status',
            'tx_hash', 'error_message', 'settlement_reference', 'settled_at',
            'created_at', 'updated_at'
        )
        read_only_fields = fields

class ClaimSerializer(serializers.ModelSerializer):
    claimant_username = serializers.ReadOnlyField(source='claimant.username')
    claimant_wallet = serializers.ReadOnlyField(source='claimant.wallet_address')
    policy_number = serializers.ReadOnlyField(source='policy.policy_number')
    policy_limit = serializers.ReadOnlyField(source='policy.coverage_limit')
    assigned_reviewer_username = serializers.ReadOnlyField(source='assigned_reviewer.username')
    evidence = SupportingEvidenceSerializer(many=True, read_only=True)
    payout_authorization = PayoutAuthorizationSerializer(read_only=True)
    review_decisions = ClaimReviewDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = Claim
        fields = (
            'id', 'claim_reference', 'claimant', 'claimant_username', 'claimant_wallet',
            'policy', 'policy_number', 'policy_limit', 'category', 'incident_description',
            'incident_date', 'requested_amount', 'approved_amount', 'authorized_payout_amount',
            'status', 'assigned_reviewer', 'assigned_reviewer_username', 'on_chain_status',
            'on_chain_tx_hash', 'evidence', 'payout_authorization', 'review_decisions',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'claim_reference', 'claimant', 'approved_amount', 'authorized_payout_amount',
            'status', 'assigned_reviewer', 'on_chain_status', 'on_chain_tx_hash',
            'created_at', 'updated_at'
        )

class ClaimCreateSerializer(serializers.ModelSerializer):
    evidence = SupportingEvidenceSerializer(many=True, required=False)

    class Meta:
        model = Claim
        fields = (
            'policy', 'category', 'incident_description',
            'incident_date', 'requested_amount', 'evidence'
        )

class ClaimApproveActionSerializer(serializers.Serializer):
    approved_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    notes = serializers.CharField(required=True, allow_blank=False)

class ClaimRejectActionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=True, allow_blank=False)

class PayoutAuthorizeActionSerializer(serializers.Serializer):
    payout_amount = serializers.DecimalField(max_digits=14, decimal_places=2)

class ClaimSettleActionSerializer(serializers.Serializer):
    settlement_reference = serializers.CharField(
        required=True,
        help_text="Confirmed Stellar Testnet payment transaction hash"
    )

class DashboardMetricsSerializer(serializers.Serializer):
    total_claims = serializers.IntegerField()
    submitted_claims = serializers.IntegerField()
    under_review_claims = serializers.IntegerField()
    approved_claims = serializers.IntegerField()
    rejected_claims = serializers.IntegerField()
    payout_authorized_claims = serializers.IntegerField()
    settled_claims = serializers.IntegerField()
    total_requested_volume = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_authorized_payout_volume = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_settled_volume = serializers.DecimalField(max_digits=16, decimal_places=2)

