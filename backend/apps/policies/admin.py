from django.contrib import admin
from .models import Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = (
        'policy_number',
        'policyholder',
        'category',
        'coverage_limit',
        'deductible',
        'start_date',
        'end_date',
        'is_active',
        'created_at',
    )
    list_filter = ('category', 'is_active', 'start_date', 'end_date')
    search_fields = ('policy_number', 'policyholder__username', 'policyholder__email')
    ordering = ('-created_at',)
    date_hierarchy = 'start_date'

