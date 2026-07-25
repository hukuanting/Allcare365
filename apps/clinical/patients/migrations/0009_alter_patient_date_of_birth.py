from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0008_alter_careplan_table_comment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True, verbose_name="Date of Birth"),
        ),
    ]
