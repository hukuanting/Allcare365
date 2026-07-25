from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fhir_integration", "0005_alter_auditlog_table_comment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fhirresource",
            name="resource_id",
            field=models.CharField(max_length=100),
        ),
    ]
