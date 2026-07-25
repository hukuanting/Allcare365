import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_productuser'),
        ('health_screening', '0010_researchaggregatereport'),
        ('oauth2_provider', '0005_auto_20211222_2352'),
        ('patients', '0009_alter_patient_date_of_birth'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SmartLaunchContext',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('token_digest', models.CharField(editable=False, max_length=64, unique=True)),
                ('target_launch_uri', models.URLField(blank=True, default='', max_length=1000)),
                ('expires_at', models.DateTimeField()),
                ('consumed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='smart_launch_contexts', to=settings.AUTH_USER_MODEL)),
                ('encounter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='smart_launch_contexts', to='health_screening.healthscreening')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='smart_launch_contexts', to='patients.patient')),
            ],
            options={
                'db_table': 'smart_launch_contexts',
                'indexes': [models.Index(fields=['expires_at', 'consumed_at'], name='smart_launc_expires_3469d5_idx')],
            },
        ),
        migrations.CreateModel(
            name='SmartAuthorizationContext',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('authorization_code_digest', models.CharField(editable=False, max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('exchanged_at', models.DateTimeField(blank=True, null=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='smart_authorization_contexts', to='oauth2_provider.application')),
                ('encounter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='smart_authorization_contexts', to='health_screening.healthscreening')),
                ('launch_context', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='authorization_context', to='authentication.smartlaunchcontext')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='smart_authorization_contexts', to='patients.patient')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='smart_authorization_contexts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'smart_authorization_contexts',
                'indexes': [models.Index(fields=['patient', 'application'], name='smart_autho_patient_e1aabf_idx')],
            },
        ),
        migrations.CreateModel(
            name='SmartAccessTokenContext',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('access_token', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='smart_patient_context', to='oauth2_provider.accesstoken')),
                ('authorization_context', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='access_token_contexts', to='authentication.smartauthorizationcontext')),
            ],
            options={'db_table': 'smart_access_token_contexts'},
        ),
        migrations.CreateModel(
            name='SmartRefreshTokenContext',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('authorization_context', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='refresh_token_contexts', to='authentication.smartauthorizationcontext')),
                ('refresh_token', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='smart_patient_context', to='oauth2_provider.refreshtoken')),
            ],
            options={'db_table': 'smart_refresh_token_contexts'},
        ),
    ]
