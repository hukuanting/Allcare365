from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fhir_integration", "0006_alter_fhirresource_resource_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="fhirresource",
            name="origin_namespace",
            field=models.CharField(
                db_index=True,
                default="unspecified",
                max_length=200,
            ),
        ),
    ]
