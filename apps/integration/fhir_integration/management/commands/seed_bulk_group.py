import uuid
from datetime import date

from django.core.management.base import BaseCommand

from apps.clinical.patients.models import Patient


BULK_PATIENTS = [
    {
        "id": "10000000-0000-4000-a000-000000000001",
        "mrn": "BULK-001",
        "first_name": "Alex",
        "last_name": "Bulk",
        "sex": "male",
        "date_of_birth": date(1980, 1, 1),
    },
    {
        "id": "10000000-0000-4000-a000-000000000002",
        "mrn": "BULK-002",
        "first_name": "Bailey",
        "last_name": "Bulk",
        "sex": "female",
        "date_of_birth": date(1990, 2, 2),
    },
    {
        "id": "10000000-0000-4000-a000-000000000003",
        "mrn": "BULK-003",
        "first_name": "Casey",
        "last_name": "Bulk",
        "sex": "female",
        "date_of_birth": date(2000, 3, 3),
    },
]


class Command(BaseCommand):
    help = "Seed deterministic patients for Inferno Bulk Data Group/example-group export."

    def handle(self, *args, **options):
        for row in BULK_PATIENTS:
            Patient.objects.update_or_create(
                id=uuid.UUID(row["id"]),
                defaults={
                    "medical_record_number": row["mrn"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "sex": row["sex"],
                    "date_of_birth": row["date_of_birth"],
                    "race": "White",
                    "ethnicity": "Not Hispanic or Latino",
                    "current_address_line1": "123 Health Dr",
                    "city": "Ann Arbor",
                    "state": "MI",
                    "postal_code": "48105",
                    "country": "US",
                    "phone_number": "+15555555555",
                    "phone_number_type": "home",
                    "email_address": f"{row['mrn'].lower()}@example.org",
                    "preferred_language": "en",
                    "occupation": "Software Engineer",
                    "occupation_industry": "Computer Systems Design",
                    "status": "active",
                },
            )

        self.stdout.write(self.style.SUCCESS("Seeded Bulk Data Group/example-group patients."))
        self.stdout.write("Patient IDs: " + ",".join(row["id"] for row in BULK_PATIENTS))
