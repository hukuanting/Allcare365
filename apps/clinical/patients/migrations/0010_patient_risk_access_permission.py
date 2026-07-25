from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0009_alter_patient_date_of_birth"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="patient",
            options={
                "permissions": [
                    (
                        "launch_any_patient_smart_context",
                        "Can launch SMART context for any patient",
                    ),
                    (
                        "run_all_patient_risk_assessments",
                        "Can run disease risk assessments for any patient",
                    ),
                ],
                "verbose_name": "Patient",
                "verbose_name_plural": "Patients",
            },
        ),
    ]
