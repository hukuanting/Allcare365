import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0011_clinical_record_access_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientUserLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("status", models.CharField(default="active", max_length=50)),
                ("start_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("end_at", models.DateTimeField(blank=True, null=True)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_links", to="patients.patient")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="patient_record_link", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "patient_user_links"},
        ),
        migrations.AddIndex(
            model_name="patientuserlink",
            index=models.Index(fields=["patient", "status"], name="patient_use_patient_3c0a7c_idx"),
        ),
        migrations.AddIndex(
            model_name="patientuserlink",
            index=models.Index(fields=["status", "start_at"], name="patient_use_status_abc742_idx"),
        ),
    ]
