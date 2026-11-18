from django.contrib import admin
from .models import TransactionRecord


@admin.register(TransactionRecord)
class TransactionRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'claim_reference',
        'tx_type',
        'status',
        'network',
        'ledger_sequence',
        'contract_id',
        'created_at',
    )
    list_filter = ('tx_type', 'status', 'network', 'created_at')
    search_fields = ('claim_reference', 'tx_hash', 'contract_id')
    readonly_fields = ('created_at', 'raw_response')
    date_hierarchy = 'created_at'

