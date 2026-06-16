from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application


class Command(BaseCommand):
    help = "Register Inferno as the Backend Services bulk data client."

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            default="inferno_bulk_client",
            help="OAuth2 client_id entered in the Inferno Bulk Data test form.",
        )

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(username="inferno_bulk_service")
        client_id = options["client_id"]

        app, created = Application.objects.update_or_create(
            client_id=client_id,
            defaults={
                "user": user,
                "client_type": "confidential",
                "authorization_grant_type": "client-credentials",
                "client_secret": "private-key-jwt-not-used",
                "name": "Inferno Bulk Data Backend Services Client",
                "skip_authorization": True,
                "algorithm": "RS384",
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Bulk Data client: {app.client_id}"))
        self.stdout.write("JWKS URL to register: https://inferno.healthit.gov/suites/custom/g10_certification/.well-known/jwks.json")
