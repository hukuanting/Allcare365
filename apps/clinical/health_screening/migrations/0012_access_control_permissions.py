from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("health_screening", "0011_observation_temporal_lookup_indexes")]

    operations = [
        migrations.AlterModelOptions(
            name="healthscreening",
            options={
                "permissions": [
                    ("import_clinical_records", "Can import clinical records"),
                    ("view_research_aggregates", "Can view governed research aggregates"),
                    ("approve_research_aggregates", "Can approve governed research aggregates"),
                ],
                "verbose_name": "就診/健康檢查",
            },
        )
    ]
