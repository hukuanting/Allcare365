"""Management utilities for active patient records."""

from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.clinical.patients.models import Patient
from apps.clinical.patients.services import (
    DuplicatePatientDetector,
    PatientDataValidator,
    PatientSearchService,
    PatientStatsService,
    patient_display_name,
    patient_email,
    patient_phone,
)


class Command(BaseCommand):
    help = "Advanced patient management operations"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", help="Available actions")

        duplicate_parser = subparsers.add_parser("find-duplicates", help="Find potential duplicate patients")
        duplicate_parser.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold")
        duplicate_parser.add_argument("--output", type=str, help="Output file for results")
        duplicate_parser.add_argument("--auto-merge", action="store_true", help="Auto-merge pairs with score >= 0.95")

        validate_parser = subparsers.add_parser("validate", help="Validate patient data")
        validate_parser.add_argument("--fix", action="store_true", help="Automatically fix normalizable fields")
        validate_parser.add_argument("--patient-id", type=str, help="Validate a specific patient by ID")

        stats_parser = subparsers.add_parser("stats", help="Generate patient statistics")
        stats_parser.add_argument("--output", type=str, help="Output file for statistics")

        search_parser = subparsers.add_parser("search", help="Search patients")
        search_parser.add_argument("--query", type=str, help="Search query")
        search_parser.add_argument("--first-name", type=str, help="First name")
        search_parser.add_argument("--last-name", type=str, help="Last name")
        search_parser.add_argument("--dob", type=str, help="Date of birth (YYYY-MM-DD)")
        search_parser.add_argument("--phone", type=str, help="Phone number")
        search_parser.add_argument("--limit", type=int, default=10, help="Maximum results")

        merge_parser = subparsers.add_parser("merge", help="Merge duplicate patients")
        merge_parser.add_argument("primary_id", type=str, help="Primary patient ID to keep")
        merge_parser.add_argument("duplicate_id", type=str, help="Duplicate patient ID to merge")
        merge_parser.add_argument("--user", type=str, default="system", help="Username performing merge")

    def handle(self, *args, **options):
        action = options.get("action")
        if not action:
            self.print_help("manage.py", "patient_manager")
            return

        try:
            if action == "find-duplicates":
                self.find_duplicates(options)
            elif action == "validate":
                self.validate_patients(options)
            elif action == "stats":
                self.generate_statistics(options)
            elif action == "search":
                self.search_patients(options)
            elif action == "merge":
                self.merge_patients(options)
            else:
                raise CommandError(f"Unknown action: {action}")
        except Exception as exc:
            raise CommandError(f"Command failed: {exc}") from exc

    def find_duplicates(self, options):
        threshold = options["threshold"]
        output_file = options.get("output")
        auto_merge = options.get("auto_merge", False)

        patients = Patient.objects.filter(is_active=True).order_by("created_at")
        total_patients = patients.count()
        all_duplicates = []
        processed_pairs = set()

        self.stdout.write(f"Analyzing {total_patients} active patients...")

        for index, patient in enumerate(patients, start=1):
            if index % 100 == 0:
                self.stdout.write(f"Progress: {index}/{total_patients}")

            duplicates = DuplicatePatientDetector.find_potential_duplicates(patient, threshold)
            for dup_patient, score, details in duplicates:
                pair_key = tuple(sorted([str(patient.id), str(dup_patient.id)]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                all_duplicates.append(
                    {
                        "primary_patient": self._patient_payload(patient),
                        "duplicate_patient": self._patient_payload(dup_patient),
                        "similarity_score": score,
                        "match_details": details,
                    }
                )

        all_duplicates.sort(key=lambda item: item["similarity_score"], reverse=True)
        self.stdout.write(f"Found {len(all_duplicates)} potential duplicate pairs")

        for index, duplicate in enumerate(all_duplicates[:10], start=1):
            self.stdout.write(f"\n{index}. Similarity: {duplicate['similarity_score']:.2f}")
            self.stdout.write(
                f"   Primary: {duplicate['primary_patient']['name']} "
                f"(DOB: {duplicate['primary_patient']['dob']})"
            )
            self.stdout.write(
                f"   Duplicate: {duplicate['duplicate_patient']['name']} "
                f"(DOB: {duplicate['duplicate_patient']['dob']})"
            )

        if auto_merge:
            self._auto_merge(all_duplicates)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as output:
                json.dump(
                    {
                        "generated_at": timezone.now().isoformat(),
                        "threshold": threshold,
                        "total_duplicates": len(all_duplicates),
                        "duplicates": all_duplicates,
                    },
                    output,
                    indent=2,
                    default=str,
                )
            self.stdout.write(f"Results saved to {output_file}")

    def _auto_merge(self, duplicates):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING("No admin user found for auto-merge"))
            return

        merged_count = 0
        for duplicate in [item for item in duplicates if item["similarity_score"] >= 0.95]:
            primary = Patient.objects.get(id=duplicate["primary_patient"]["id"])
            dup_patient = Patient.objects.get(id=duplicate["duplicate_patient"]["id"])
            if dup_patient.created_at < primary.created_at:
                primary, dup_patient = dup_patient, primary
            with transaction.atomic():
                DuplicatePatientDetector.merge_patients(primary, dup_patient, admin_user)
            merged_count += 1

        self.stdout.write(f"Auto-merged {merged_count} duplicate pairs")

    def validate_patients(self, options):
        patient_id = options.get("patient_id")
        fix_issues = options.get("fix", False)

        if patient_id:
            patients = [Patient.objects.get(id=patient_id)]
        else:
            patients = Patient.objects.filter(is_active=True)

        total_patients = len(patients) if isinstance(patients, list) else patients.count()
        issues_found = 0
        issues_fixed = 0
        self.stdout.write(f"Validating {total_patients} patients...")

        for index, patient in enumerate(patients, start=1):
            if index % 100 == 0:
                self.stdout.write(f"Progress: {index}/{total_patients}")

            patient_data = {
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "date_of_birth": patient.date_of_birth,
                "sex": patient.sex,
                "phone_number": patient.phone_number,
                "email_address": patient.email_address,
            }
            is_valid, errors = PatientDataValidator.validate_patient_data(patient_data)
            if is_valid:
                continue

            issues_found += 1
            self.stdout.write(self.style.WARNING(f"Patient {patient_display_name(patient)} ({patient.id}):"))
            for error in errors:
                self.stdout.write(f"   - {error}")

            if fix_issues and self._fix_patient_issues(patient):
                issues_fixed += 1

        self.stdout.write("\nValidation summary:")
        self.stdout.write(f"   Total patients checked: {total_patients}")
        self.stdout.write(f"   Issues found: {issues_found}")
        if fix_issues:
            self.stdout.write(f"   Issues fixed: {issues_fixed}")

    def _fix_patient_issues(self, patient):
        normalized_data = PatientDataValidator.normalize_patient_data(
            {
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "middle_name": patient.middle_name,
                "sex": patient.sex,
                "phone_number": patient.phone_number,
                "email_address": patient.email_address,
                "current_address_line1": patient.current_address_line1,
                "current_address_line2": patient.current_address_line2,
                "city": patient.city,
                "state": patient.state,
                "postal_code": patient.postal_code,
            }
        )

        changed_fields = []
        for field, value in normalized_data.items():
            if hasattr(patient, field) and getattr(patient, field) != value:
                setattr(patient, field, value)
                changed_fields.append(field)

        if changed_fields:
            patient.save(update_fields=changed_fields + ["updated_at"])
            return True
        return False

    def generate_statistics(self, options):
        stats = PatientStatsService.get_patient_demographics()
        output_file = options.get("output")

        self.stdout.write(f"Total patients: {stats['total_patients']}")
        self.stdout.write("\nSex distribution:")
        for sex, count in stats["sex_distribution"].items():
            percentage = (count / stats["total_patients"] * 100) if stats["total_patients"] else 0
            self.stdout.write(f"   {sex}: {count} ({percentage:.1f}%)")

        self.stdout.write("\nAge distribution:")
        for age_group, count in stats["age_distribution"].items():
            percentage = (count / stats["total_patients"] * 100) if stats["total_patients"] else 0
            self.stdout.write(f"   {age_group}: {count} ({percentage:.1f}%)")

        if output_file:
            with open(output_file, "w", encoding="utf-8") as output:
                json.dump(
                    {"generated_at": timezone.now().isoformat(), "statistics": stats},
                    output,
                    indent=2,
                    default=str,
                )
            self.stdout.write(f"Statistics saved to {output_file}")

    def search_patients(self, options):
        search_params = {
            "query": options.get("query"),
            "first_name": options.get("first_name"),
            "last_name": options.get("last_name"),
            "date_of_birth": options.get("dob"),
            "phone": options.get("phone"),
            "limit": options.get("limit", 10),
        }
        search_params = {key: value for key, value in search_params.items() if value is not None}

        if not any(search_params.values()):
            raise CommandError("At least one search parameter is required")

        results = PatientSearchService.search_patients(**search_params)
        self.stdout.write(f"Found {len(results)} patients:")

        for index, patient in enumerate(results, start=1):
            self.stdout.write(f"\n{index}. {patient_display_name(patient)}")
            self.stdout.write(f"   ID: {patient.id}")
            self.stdout.write(f"   DOB: {patient.date_of_birth}")
            self.stdout.write(f"   Phone: {patient_phone(patient) or 'N/A'}")
            self.stdout.write(f"   Email: {patient_email(patient) or 'N/A'}")
            self.stdout.write(f"   Created: {patient.created_at:%Y-%m-%d}")

    def merge_patients(self, options):
        primary_id = options["primary_id"]
        duplicate_id = options["duplicate_id"]
        username = options.get("user", "system")

        primary_patient = Patient.objects.get(id=primary_id, is_active=True)
        duplicate_patient = Patient.objects.get(id=duplicate_id, is_active=True)

        if username == "system":
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise CommandError("No admin user found for system merge")
        else:
            user = User.objects.get(username=username)

        self.stdout.write(f"Primary patient: {patient_display_name(primary_patient)} ({primary_patient.id})")
        self.stdout.write(f"Duplicate patient: {patient_display_name(duplicate_patient)} ({duplicate_patient.id})")

        with transaction.atomic():
            merge_result = DuplicatePatientDetector.merge_patients(primary_patient, duplicate_patient, user)

        self.stdout.write("Merge completed successfully")
        for category, count in merge_result["merged_data"].items():
            self.stdout.write(f"   {category}: {count}")

    @staticmethod
    def _patient_payload(patient):
        return {
            "id": str(patient.id),
            "name": patient_display_name(patient),
            "dob": str(patient.date_of_birth),
            "phone": patient_phone(patient),
            "email": patient_email(patient),
            "created_at": patient.created_at.isoformat(),
        }
