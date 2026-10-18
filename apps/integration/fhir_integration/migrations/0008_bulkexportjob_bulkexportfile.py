import apps.integration.fhir_integration.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("fhir_integration", "0007_fhirresource_origin_namespace"),
    ]

    operations = [
        migrations.CreateModel(
            name="BulkExportJob",
            fields=[
                ("id", models.CharField(editable=False, max_length=96, primary_key=True, serialize=False)),
                ("owner_client_id", models.CharField(db_index=True, max_length=255)),
                ("export_type", models.CharField(max_length=16)),
                ("group_id", models.CharField(blank=True, default="", max_length=100)),
                ("resource_types", models.JSONField(default=list)),
                ("patient_ids", models.JSONField(default=list)),
                ("request_url", models.TextField()),
                ("transaction_time", models.DateTimeField()),
                ("since", models.CharField(blank=True, default="", max_length=1000)),
                ("type_filter", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("completed", "Completed"), ("cancelled", "Cancelled"), ("failed", "Failed")], default="completed", max_length=16)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "indexes": [models.Index(fields=["owner_client_id", "expires_at"], name="fhir_integr_owner_c_bba0c6_idx")],
            },
        ),
        migrations.CreateModel(
            name="BulkExportFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource_type", models.CharField(max_length=50)),
                ("content", models.FileField(max_length=500, upload_to=apps.integration.fhir_integration.models.bulk_export_upload_path)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="files", to="fhir_integration.bulkexportjob")),
            ],
        ),
        migrations.AddConstraint(
            model_name="bulkexportfile",
            constraint=models.UniqueConstraint(fields=("job", "resource_type"), name="unique_bulk_export_file_type"),
        ),
    ]
