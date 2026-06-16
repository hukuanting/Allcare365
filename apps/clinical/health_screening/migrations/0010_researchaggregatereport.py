# Generated manually for aggregate research export governance.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('health_screening', '0009_alter_aianalysisjob_table_comment_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ResearchAggregateReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('title', models.CharField(max_length=250)),
                ('report_type', models.CharField(choices=[('cohort_summary', 'Cohort Summary'), ('cohort_measure_report', 'FHIR MeasureReport'), ('patients_like_this', 'Patients Like This')], default='cohort_summary', max_length=100)),
                ('status', models.CharField(choices=[('requested', 'Requested'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='requested', max_length=50)),
                ('dataset', models.CharField(default='h2u_cvd_csv', max_length=100)),
                ('query_params_json', models.JSONField(blank=True, default=dict)),
                ('privacy_json', models.JSONField(blank=True, default=dict)),
                ('result_json', models.JSONField(blank=True, default=dict)),
                ('fhir_json', models.JSONField(blank=True, default=dict)),
                ('approval_note', models.TextField(blank=True, default='')),
                ('requested_at', models.DateTimeField(default=timezone.now)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('rejected_at', models.DateTimeField(blank=True, null=True)),
                ('metadata_json', models.JSONField(blank=True, default=dict)),
                ('approved_by_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_research_aggregate_reports', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('requested_by_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requested_research_aggregate_reports', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'research_aggregate_reports',
                'indexes': [
                    models.Index(fields=['status', '-requested_at'], name='research_ag_status_42b779_idx'),
                    models.Index(fields=['report_type', 'status'], name='research_ag_report__2b3732_idx'),
                    models.Index(fields=['requested_by_user', '-requested_at'], name='research_ag_request_f52721_idx'),
                    models.Index(fields=['approved_by_user', '-approved_at'], name='research_ag_approve_6938f0_idx'),
                ],
            },
        ),
    ]
