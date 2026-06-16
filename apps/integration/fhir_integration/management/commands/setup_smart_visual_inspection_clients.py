from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application


INFERNO_REDIRECT_URIS = " ".join([
    "https://inferno.healthit.gov/suites/custom/smart/redirect",
    "https://inferno.healthit.gov/suites/custom/g10_certification/callback",
    "https://inferno.healthit.gov/suites/custom/g10_certification/redirect",
    "https://inferno.healthit.gov/suites/g10_certification/callback",
    "https://inferno.healthit.gov/suites/g10_certification/redirect",
])


class Command(BaseCommand):
    help = "Register SMART App Launch clients used by Inferno g10 section 9 visual inspection tests."

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(username="inferno_user")

        clients = [
            {
                "client_id": "inferno_public_client",
                "name": "Inferno Public Standalone Client",
                "client_type": "public",
                "client_secret": "",
                "skip_authorization": False,
                "algorithm": "RS256",
            },
            {
                "client_id": "inferno_asymmetric_client",
                "name": "Inferno Asymmetric Standalone Client",
                "client_type": "confidential",
                "client_secret": "private-key-jwt-not-used",
                "skip_authorization": False,
                "algorithm": "RS256",
            },
        ]

        for client in clients:
            app, created = Application.objects.update_or_create(
                client_id=client["client_id"],
                defaults={
                    "user": user,
                    "client_type": client["client_type"],
                    "authorization_grant_type": "authorization-code",
                    "client_secret": client["client_secret"],
                    "name": client["name"],
                    "redirect_uris": INFERNO_REDIRECT_URIS,
                    "skip_authorization": client["skip_authorization"],
                    "algorithm": client["algorithm"],
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} SMART client: {app.client_id}"))

        self.stdout.write("Use Bulk client separately: inferno_bulk_client")
