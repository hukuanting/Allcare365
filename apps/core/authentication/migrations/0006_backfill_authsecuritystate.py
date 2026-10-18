from django.conf import settings
from django.db import migrations


def create_security_states(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    UserModel = apps.get_model(app_label, model_name)
    AuthSecurityState = apps.get_model('authentication', 'AuthSecurityState')
    existing_user_ids = AuthSecurityState.objects.values_list('user_id', flat=True)
    AuthSecurityState.objects.bulk_create(
        [AuthSecurityState(user_id=user_id) for user_id in UserModel.objects.exclude(pk__in=existing_user_ids).values_list('pk', flat=True)],
        ignore_conflicts=True,
        batch_size=1000,
    )


class Migration(migrations.Migration):

    dependencies = [('authentication', '0005_authsecuritystate')]

    operations = [migrations.RunPython(create_security_states, migrations.RunPython.noop)]
