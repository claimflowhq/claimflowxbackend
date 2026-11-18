from rest_framework import serializers
from .models import Policy

class PolicySerializer(serializers.ModelSerializer):
    policyholder_username = serializers.ReadOnlyField(source='policyholder.username')

    class Meta:
        model = Policy
        fields = (
            'id', 'policy_number', 'policyholder', 'policyholder_username',
            'category', 'coverage_limit', 'deductible', 'start_date', 'end_date',
            'is_active', 'terms_summary', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

