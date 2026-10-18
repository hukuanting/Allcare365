from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("patients", "0010_patient_risk_access_permission")]

    operations = [
        migrations.AlterModelOptions(
            name="patient",
            options={
                "permissions": [
                    ("access_all_clinical_records", "Can access all clinical patient records"),
                    ("edit_all_clinical_records", "Can edit all clinical patient records"),
                    ("create_patient_records", "Can create patient records"),
                    ("launch_any_patient_smart_context", "Can launch SMART context for any patient"),
                    ("run_all_patient_risk_assessments", "Can run disease risk assessments for any patient"),
                ],
                "verbose_name": "Patient",
                "verbose_name_plural": "Patients",
            },
        )
    ]
