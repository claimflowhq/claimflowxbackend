from rest_framework import serializers
from .models import TransactionRecord

class TransactionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionRecord
        fields = (
            'id', 'claim_reference', 'tx_hash', 'tx_type', 'status',
            'network', 'contract_id', 'ledger_sequence', 'explorer_url',
            'error_message', 'raw_response', 'created_at'
        )
        read_only_fields = fields

class ContractInfoSerializer(serializers.Serializer):
    contract_id = serializers.CharField()
    network = serializers.CharField()
    rpc_url = serializers.CharField()
    admin_address = serializers.CharField()
    explorer_url = serializers.URLField()
    status = serializers.CharField()
    simulated = serializers.BooleanField()

class OnChainClaimSerializer(serializers.Serializer):
    claim_id = serializers.CharField()
    claimant = serializers.CharField()
    policy_id = serializers.CharField()
    requested_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    approved_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    authorized_payout_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    status = serializers.CharField()
    reviewer = serializers.CharField(allow_null=True)
    decision_notes = serializers.CharField(allow_blank=True)
    settlement_ref = serializers.CharField(allow_blank=True)
    updated_at = serializers.IntegerField()
    contract_id = serializers.CharField()
    network = serializers.CharField()

