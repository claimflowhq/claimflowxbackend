import os
from django.core.management.base import BaseCommand
from apps.authentication.models import User, UserRole


class Command(BaseCommand):
    help = "Idempotently create or update the default ClaimFlow superuser"

    def add_arguments(self, parser):
        parser.add_argument('--username', default=os.getenv('SUPERUSER_USERNAME', 'claimflow'))
        parser.add_argument('--password', default=os.getenv('SUPERUSER_PASSWORD', 'claimflow2025'))
        parser.add_argument('--email', default=os.getenv('SUPERUSER_EMAIL', 'admin@claimflowx.com'))

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )

        user.set_password(password)
        user.email = email
        user.role = UserRole.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Successfully created superuser '{username}'."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated superuser '{username}'."))

