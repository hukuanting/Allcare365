"""Durable, private storage for FHIR Bulk Data export jobs and output files."""

from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .models import BulkExportFile, BulkExportJob


class BulkExportStorageError(RuntimeError):
    """Raised when a production deployment has not configured private object storage."""


class BulkExportJobStore:
    """Database-backed job lifecycle with bounded retention and private FileField storage."""

    @staticmethod
    def _require_private_storage():
        # Local/test environments may use Django's filesystem storage. Production
        # must explicitly opt in after configuring a private shared object store.
        if not settings.DEBUG and not getattr(settings, "BULK_EXPORT_STORAGE_PRIVATE", False):
            raise BulkExportStorageError(
                "Bulk export storage is not configured as private shared storage."
            )

    @staticmethod
    def expiry_time():
        seconds = int(getattr(settings, "BULK_EXPORT_TTL_SECONDS", 600))
        return timezone.now() + timedelta(seconds=max(1, seconds))

    @classmethod
    def create(cls, **job_fields):
        cls._require_private_storage()
        return BulkExportJob.objects.create(expires_at=cls.expiry_time(), **job_fields)

    @staticmethod
    def _delete_files(job):
        for export_file in job.files.all():
            if export_file.content:
                export_file.content.delete(save=False)

    @classmethod
    def purge_expired(cls, now=None):
        now = now or timezone.now()
        count = 0
        for job_id in BulkExportJob.objects.filter(expires_at__lte=now).values_list("pk", flat=True).iterator():
            with transaction.atomic():
                job = (
                    BulkExportJob.objects.select_for_update()
                    .prefetch_related("files")
                    .filter(pk=job_id, expires_at__lte=now)
                    .first()
                )
                if job is not None:
                    cls._delete_files(job)
                    job.delete()
                    count += 1
        return count

    @classmethod
    def get_active(cls, job_id):
        job = BulkExportJob.objects.prefetch_related("files").filter(pk=job_id).first()
        if job is None or job.status == BulkExportJob.STATUS_CANCELLED:
            return None
        if job.expires_at > timezone.now():
            return job

        # Request paths only clean the referenced job. The scheduled command
        # performs the full bounded-retention sweep without unauthenticated
        # callers being able to trigger a global storage operation.
        with transaction.atomic():
            expired_job = (
                BulkExportJob.objects.select_for_update()
                .prefetch_related("files")
                .filter(pk=job_id, expires_at__lte=timezone.now())
                .first()
            )
            if expired_job is not None:
                cls._delete_files(expired_job)
                expired_job.delete()
        return None

    @staticmethod
    def get_output(job, resource_type):
        return job.files.filter(resource_type=resource_type).first()

    @classmethod
    def cancel(cls, job):
        with transaction.atomic():
            locked_job = BulkExportJob.objects.select_for_update().get(pk=job.pk)
            cls._delete_files(locked_job)
            locked_job.files.all().delete()
            locked_job.status = BulkExportJob.STATUS_CANCELLED
            locked_job.save(update_fields=["status", "updated_at"])

    @classmethod
    def get_or_create_output(cls, job, resource_type, render):
        """Return an existing immutable output or render and persist it once."""
        cls._require_private_storage()
        with transaction.atomic():
            locked_job = BulkExportJob.objects.select_for_update().get(pk=job.pk)
            if locked_job.status != BulkExportJob.STATUS_COMPLETED:
                return None
            try:
                return locked_job.files.get(resource_type=resource_type)
            except BulkExportFile.DoesNotExist:
                pass

            export_file = BulkExportFile(job=locked_job, resource_type=resource_type)
            try:
                output = render()
                export_file.content.save(
                    f"{resource_type.lower()}.ndjson", ContentFile(output), save=False
                )
                export_file.save()
            except Exception:
                if export_file.content:
                    export_file.content.delete(save=False)
                cls._delete_files(locked_job)
                locked_job.files.all().delete()
                locked_job.status = BulkExportJob.STATUS_FAILED
                locked_job.save(update_fields=["status", "updated_at"])
                raise
            return export_file
