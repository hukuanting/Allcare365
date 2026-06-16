# Generated manually on 2026-06-10

from django.db import migrations


AUDIT_LOG_LEGACY_DEFAULTS_SQL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_logs' AND column_name = 'table_name'
    ) THEN
        ALTER TABLE audit_logs ALTER COLUMN table_name SET DEFAULT '';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_logs' AND column_name = 'record_id'
    ) THEN
        ALTER TABLE audit_logs ALTER COLUMN record_id SET DEFAULT '';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_logs' AND column_name = 'timestamp'
    ) THEN
        ALTER TABLE audit_logs ALTER COLUMN "timestamp" SET DEFAULT CURRENT_TIMESTAMP;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_logs' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE audit_logs ALTER COLUMN is_active SET DEFAULT true;
    END IF;

    ALTER TABLE audit_logs ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
    ALTER TABLE audit_logs ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('fhir_integration', '0003_auditlog_fhirresourcemapping'),
    ]

    operations = [
        migrations.RunSQL(AUDIT_LOG_LEGACY_DEFAULTS_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
