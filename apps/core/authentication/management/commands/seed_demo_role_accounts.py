from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.authentication.models import ProductUser, UserProfile


DEMO_ROLE_ACCOUNTS = [
    {"role": "admin", "username": "admin", "password": "admin123456", "display_name": "System Admin", "is_staff": True, "is_superuser": True},
    {"role": "patient", "username": "patient", "password": "patient123456", "display_name": "Demo Patient"},
    {"role": "researcher", "username": "researcher", "password": "researcher123456", "display_name": "Demo Researcher"},
    {"role": "analyst", "username": "analyst", "password": "analyst123456", "display_name": "Demo Analyst"},
    {"role": "clinician", "username": "clinician", "password": "clinician123456", "display_name": "Demo Clinician", "is_staff": True},
    {"role": "doctor", "username": "doctor", "password": "doctor123456", "display_name": "Demo Doctor", "is_staff": True},
    {"role": "physician", "username": "physician", "password": "physician123456", "display_name": "Demo Physician", "is_staff": True},
    {"role": "nurse", "username": "nurse", "password": "nurse123456", "display_name": "Demo Nurse", "is_staff": True},
    {"role": "provider", "username": "provider", "password": "provider123456", "display_name": "Demo Provider", "is_staff": True},
    {"role": "staff", "username": "staff", "password": "staff123456", "display_name": "Demo Staff", "is_staff": True},
    {"role": "device_client", "username": "device_client", "password": "device_client123456", "display_name": "Demo Device Client"},
    {"role": "system_service", "username": "system_service", "password": "system_service123456", "display_name": "Demo System Service", "is_staff": True},
]


class Command(BaseCommand):
    help = "Seed deterministic demo users for each product role."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-passwords",
            action="store_true",
            help="Do not reset passwords for existing demo users.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        keep_passwords = bool(options.get("keep_passwords"))
        for account in DEMO_ROLE_ACCOUNTS:
            user, created = User.objects.get_or_create(
                username=account["username"],
                defaults={
                    "email": f"{account['username']}@allcare365.local",
                    "first_name": account["display_name"].split(" ", 1)[0],
                    "last_name": account["display_name"].split(" ", 1)[-1],
                    "is_active": True,
                    "is_staff": bool(account.get("is_staff", False)),
                    "is_superuser": bool(account.get("is_superuser", False)),
                },
            )
            user.email = f"{account['username']}@allcare365.local"
            user.first_name = account["display_name"].split(" ", 1)[0]
            user.last_name = account["display_name"].split(" ", 1)[-1]
            user.is_active = True
            user.is_staff = bool(account.get("is_staff", False))
            user.is_superuser = bool(account.get("is_superuser", False))
            if created or not keep_passwords:
                user.set_password(account["password"])
            user.save()

            ProductUser.objects.update_or_create(
                auth_user=user,
                defaults={
                    "display_name": account["display_name"],
                    "role": account["role"],
                    "status": "active",
                    "organization_name": "AllCare365 Demo",
                    "metadata_json": {"demo_account": True},
                },
            )

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = "patient" if account["role"] == "patient" else "professional"
            profile.save(update_fields=["role", "updated_at"])

            group, _ = Group.objects.get_or_create(name=account["role"])
            user.groups.add(group)

            state = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{state}: {account['username']} / {account['password']} ({account['role']})"
                )
            )
