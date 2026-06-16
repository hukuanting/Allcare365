# Generated manually to add detailed lifestyle questionnaire fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('health_screening', '0003_alter_healthscreening_unique_together_and_more'),
    ]

    operations = [
        # Add detailed exercise fields
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='exercise_intensity',
            field=models.CharField(blank=True, choices=[('light', '輕度運動 (散步、伸展)'), ('moderate', '中度運動 (快走、游泳、騎車)'), ('vigorous', '高強度運動 (跑步、球類運動)'), ('intense', '劇烈運動 (競技運動、重訓)')], max_length=20, null=True, verbose_name='運動強度'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='exercise_duration',
            field=models.CharField(blank=True, choices=[('<15', '少於15分鐘'), ('15-30', '15-30分鐘'), ('30-60', '30-60分鐘'), ('60-90', '60-90分鐘'), ('>90', '超過90分鐘')], max_length=10, null=True, verbose_name='每次運動時間'),
        ),
        
        # Add additional family history fields
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='family_hyperlipidemia',
            field=models.BooleanField(blank=True, null=True, verbose_name='家族高血脂史'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='family_stroke',
            field=models.BooleanField(blank=True, null=True, verbose_name='家族中風史'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='family_other_diseases',
            field=models.TextField(blank=True, null=True, verbose_name='其他家族疾病史'),
        ),
        
        # Add detailed personal medical history fields
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='personal_diabetes_type',
            field=models.CharField(blank=True, choices=[('type1', '第一型糖尿病'), ('type2', '第二型糖尿病'), ('gestational', '妊娠糖尿病'), ('other', '其他類型')], max_length=20, null=True, verbose_name='糖尿病類型'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='personal_diabetes_years',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='糖尿病患病年數'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='personal_heart_disease_type',
            field=models.CharField(blank=True, choices=[('coronary', '冠心病'), ('myocardial', '心肌梗塞'), ('arrhythmia', '心律不整'), ('valve', '心瓣膜疾病'), ('other', '其他心臟疾病')], max_length=20, null=True, verbose_name='心臟病類型'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='personal_hypertension_years',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='高血壓患病年數'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='personal_hyperlipidemia_years',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='高血脂患病年數'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='personal_stroke',
            field=models.BooleanField(blank=True, null=True, verbose_name='個人中風史'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='personal_other_diseases',
            field=models.TextField(blank=True, null=True, verbose_name='其他個人疾病史'),
        ),
        
        # Add detailed alcohol information
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='alcohol_type',
            field=models.CharField(blank=True, choices=[('beer', '啤酒'), ('wine', '葡萄酒'), ('spirits', '烈酒'), ('mixed', '混合飲用')], max_length=20, null=True, verbose_name='主要飲酒類型'),
        ),
        
        # Add medication and allergy history
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='current_medications',
            field=models.TextField(blank=True, null=True, verbose_name='目前用藥'),
        ),
        migrations.AddField(
            model_name='lifestylequestionnaire',
            name='allergies',
            field=models.TextField(blank=True, null=True, verbose_name='過敏史'),
        ),
    ]