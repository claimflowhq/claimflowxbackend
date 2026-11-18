from django.contrib import admin
from .models import (
    Claim,
    SupportingEvidence,
    ClaimReviewDecision,
    PayoutAuthorization,
    ClaimTimelineEvent,
)


class SupportingEvidenceInline(admin.TabularInline):
    model = SupportingEvidence
    extra = 0
    readonly_fields = ('uploaded_at',)


class ClaimReviewDecisionInline(admin.StackedInline):
    model = ClaimReviewDecision
    extra = 0
    readonly_fields = ('created_at',)


class PayoutAuthorizationInline(admin.StackedInline):
    model = PayoutAuthorization
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class ClaimTimelineEventInline(admin.TabularInline):
    model = ClaimTimelineEvent
    extra = 0
    readonly_fields = ('timestamp',)


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        'claim_reference',
        'claimant',
        'policy',
        'category',
        'requested_amount',
        'approved_amount',
        'authorized_payout_amount',
        'status',
        'on_chain_status',
        'assigned_reviewer',
        'created_at',
    )
    list_filter = ('status', 'on_chain_status', 'category', 'created_at')
    search_fields = ('claim_reference', 'claimant__username', 'claimant__email', 'on_chain_tx_hash')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [
        SupportingEvidenceInline,
        ClaimReviewDecisionInline,
        PayoutAuthorizationInline,
        ClaimTimelineEventInline,
    ]
    date_hierarchy = 'created_at'


@admin.register(SupportingEvidence)
class SupportingEvidenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'claim', 'file_name', 'document_type', 'file_size_bytes', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('file_name', 'claim__claim_reference')
    readonly_fields = ('uploaded_at',)


@admin.register(ClaimReviewDecision)
class ClaimReviewDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'claim', 'reviewer', 'decision', 'approved_amount', 'tx_hash', 'created_at')
    list_filter = ('decision', 'created_at')
    search_fields = ('claim__claim_reference', 'reviewer__username', 'tx_hash')
    readonly_fields = ('created_at',)


@admin.register(PayoutAuthorization)
class PayoutAuthorizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'claim', 'authorized_by', 'amount', 'status', 'tx_hash', 'settled_at', 'created_at')
    list_filter = ('status', 'created_at', 'settled_at')
    search_fields = ('claim__claim_reference', 'authorized_by__username', 'tx_hash', 'settlement_reference')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ClaimTimelineEvent)
class ClaimTimelineEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'claim', 'actor', 'action', 'from_status', 'to_status', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('claim__claim_reference', 'action', 'tx_hash')
    readonly_fields = ('timestamp',)

