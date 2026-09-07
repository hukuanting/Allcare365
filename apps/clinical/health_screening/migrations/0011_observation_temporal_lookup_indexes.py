from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("health_screening", "0010_researchaggregatereport"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="observation",
            index=models.Index(
                fields=["patient", "code", "-effective_at"],
                name="obs_patient_code_eff_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="observation",
            index=models.Index(
                fields=["patient", "observation_type", "-effective_at"],
                name="obs_patient_type_eff_idx",
            ),
        ),
    ]
