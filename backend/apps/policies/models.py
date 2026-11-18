from django.db import models
from django.conf import settings

class PolicyCategory(models.TextChoices):
    HEALTH = 'HEALTH', 'Health Insurance'
    AUTO = 'AUTO', 'Automobile Insurance'
    PROPERTY = 'PROPERTY', 'Property & Casualty'
    LIFE = 'LIFE', 'Life Insurance'
    TRAVEL = 'TRAVEL', 'Travel Insurance'

class Policy(models.Model):
    policy_number = models.CharField(max_length=64, unique=True, db_index=True)
    policyholder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='policies'
    )
    category = models.CharField(
        max_length=32,
        choices=PolicyCategory.choices,
        default=PolicyCategory.HEALTH
    )
    coverage_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Maximum coverage limit in USDC equivalent"
    )
    deductible = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
        help_text="Policyholder deductible"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    terms_summary = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Policies'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.policy_number} - {self.policyholder.username} ({self.category})"

