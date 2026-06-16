from django.core.management.base import BaseCommand
from django.core.management import call_command
from oauth2_provider.models import Application
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Setup OAuth2 Application for EHR Launch testing'

    def handle(self, *args, **options):
        # 1. Ensure User exists
        user, _ = User.objects.get_or_create(username='inferno_user')

        redirect_uris = (
            "https://inferno.healthit.gov/suites/custom/smart/redirect "
            "https://inferno.healthit.gov/suites/custom/g10_certification/callback"
        )
        clients = [
            ("inferno_ehr_client", "inferno_ehr_secret", "Inferno EHR App"),
            ("inferno_client_id", "inferno_client_secret", "Inferno Default SMART App"),
        ]

        for client_id, client_secret, name in clients:
            app, _ = Application.objects.update_or_create(
                client_id=client_id,
                defaults={
                    "user": user,
                    "client_type": "confidential",
                    "authorization_grant_type": "authorization-code",
                    "client_secret": client_secret,
                    "name": name,
                    "redirect_uris": redirect_uris,
                    "skip_authorization": False,
                    "algorithm": "RS256",
                },
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully setup EHR App: {app.client_id}'))
            self.stdout.write(f'Client ID: {client_id}')
            self.stdout.write(f'Client Secret: {client_secret}')
        call_command("setup_bulk_inferno_client")
        call_command("setup_smart_visual_inspection_clients")
