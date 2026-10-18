"""Explicit, auditable rollout command for invalidating existing credentials."""

from django.core.management.base import BaseCommand

from apps.core.authentication.services import invalidate_user_tokens


class Command(BaseCommand):
    help = (
        'Invalidate every user credential generation for a security rollout. '
        'Runs as a dry-run unless --apply is explicitly supplied.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Perform revocation. Omitting this flag only reports aggregate counts.',
        )

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from oauth2_provider.models import AccessToken, RefreshToken as OAuthRefreshToken

        User = get_user_model()
        summary = {
            'users': User.objects.count(),
            'oauth_access_tokens': AccessToken.objects.count(),
            'oauth_active_refresh_tokens': OAuthRefreshToken.objects.filter(revoked__isnull=True).count(),
            'jwt_outstanding_tokens': 0,
        }
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

            summary['jwt_outstanding_tokens'] = OutstandingToken.objects.count()
        except (ImportError, RuntimeError):
            pass

        summary_text = ', '.join(f'{name}={count}' for name, count in summary.items())
        if not options['apply']:
            self.stdout.write(self.style.WARNING(f'DRY RUN: {summary_text}'))
            self.stdout.write('No credentials were changed. Re-run with --apply to revoke all credentials.')
            return

        for user in User.objects.order_by('pk').iterator(chunk_size=500):
            invalidate_user_tokens(user)

        self.stdout.write(self.style.SUCCESS(f'Credentials revoked: {summary_text}'))
