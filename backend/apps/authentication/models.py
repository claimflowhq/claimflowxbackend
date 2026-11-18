from django.contrib.auth.models import AbstractUser
from django.db import models

class UserRole(models.TextChoices):
    CLAIMANT = 'CLAIMANT', 'Claimant'
    REVIEWER = 'REVIEWER', 'Reviewer'
    ADMIN = 'ADMIN', 'Admin'

class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CLAIMANT,
        help_text="Role determining permissions in ClaimFlow lifecycle"
    )
    wallet_address = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Stellar Testnet public key (e.g. G...)"
    )
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ['email', 'role']

    @property
    def is_claimant(self):
        return self.role == UserRole.CLAIMANT

    @property
    def is_reviewer(self):
        return self.role == UserRole.REVIEWER

    @property
    def is_admin_user(self):
        return self.role == UserRole.ADMIN or self.is_superuser

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

