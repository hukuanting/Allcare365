"""Patient domain services aligned with the active USCDI/FHIR patient model."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
import re
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone

from .models import InsuranceData, Patient, PatientDocument


def patient_display_name(patient: Patient) -> str:
    """Return the product's canonical display name for a patient."""
    return f"{patient.last_name}{patient.first_name}".strip() or str(patient.id)


def patient_phone(patient: Patient) -> str:
    return patient.phone_number or ""


def patient_email(patient: Patient) -> str:
    return patient.email_address or ""


def _normalize_date(value: Any) -> Optional[Any]:
    if not value:
        return None
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_sex(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    aliases = {
        "male": "M",
        "m": "M",
        "female": "F",
        "f": "F",
        "other": "O",
        "o": "O",
        "unknown": "U",
        "u": "U",
    }
    return aliases.get(value.lower(), value)


def _copy_if_blank(primary: Patient, duplicate: Patient, field: str, updated_fields: List[str]) -> None:
    if not getattr(primary, field, None) and getattr(duplicate, field, None):
        setattr(primary, field, getattr(duplicate, field))
        updated_fields.append(field)


class PatientSearchService:
    """Search patients with exact filters and lightweight fuzzy name matching."""

    @staticmethod
    def search_patients(
        query: str = None,
        first_name: str = None,
        last_name: str = None,
        date_of_birth: str = None,
        phone: str = None,
        email: str = None,
        medical_record_number: str = None,
        insurance_id: str = None,
        fuzzy_match: bool = True,
        limit: int = 50,
    ) -> List[Patient]:
        queryset = Patient.objects.filter(is_active=True)

        if query:
            q_objects = Q()
            for term in str(query).strip().split():
                q_objects |= (
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(middle_name__icontains=term)
                    | Q(medical_record_number__icontains=term)
                    | Q(phone_number__icontains=term)
                    | Q(email_address__icontains=term)
                )
            queryset = queryset.filter(q_objects)

        if first_name:
            lookup = "first_name__icontains" if fuzzy_match else "first_name__iexact"
            queryset = queryset.filter(**{lookup: first_name})

        if last_name:
            lookup = "last_name__icontains" if fuzzy_match else "last_name__iexact"
            queryset = queryset.filter(**{lookup: last_name})

        dob = _normalize_date(date_of_birth)
        if dob:
            queryset = queryset.filter(date_of_birth=dob)

        if phone:
            normalized_phone = PatientSearchService.normalize_phone(phone)
            queryset = queryset.filter(phone_number__icontains=normalized_phone or phone)

        if email:
            queryset = queryset.filter(email_address__iexact=email)

        if medical_record_number:
            queryset = queryset.filter(medical_record_number__iexact=medical_record_number)

        if insurance_id:
            queryset = queryset.filter(
                Q(insurance_info__member_identifier__icontains=insurance_id)
                | Q(insurance_info__subscriber_identifier__icontains=insurance_id)
            )

        if first_name or last_name:
            queryset = queryset.order_by("last_name", "first_name")
        else:
            queryset = queryset.order_by("-updated_at")

        return list(queryset.distinct()[:limit])

    @staticmethod
    def normalize_phone(phone: str) -> str:
        return re.sub(r"[^\d]", "", str(phone or ""))

    @staticmethod
    def search_by_demographics(
        first_name: str,
        last_name: str,
        date_of_birth: str,
        threshold: float = 0.8,
    ) -> List[Tuple[Patient, float]]:
        dob = _normalize_date(date_of_birth)
        if not dob:
            return []

        candidates = Patient.objects.filter(date_of_birth=dob, is_active=True)
        results = []
        for patient in candidates:
            first_name_sim = SequenceMatcher(
                None,
                str(first_name or "").lower(),
                patient.first_name.lower(),
            ).ratio()
            last_name_sim = SequenceMatcher(
                None,
                str(last_name or "").lower(),
                patient.last_name.lower(),
            ).ratio()
            score = (first_name_sim * 0.4) + (last_name_sim * 0.6)
            if score >= threshold:
                results.append((patient, score))

        results.sort(key=lambda item: item[1], reverse=True)
        return results


class DuplicatePatientDetector:
    """Detect and merge duplicate patients using active patient model fields."""

    RELATED_PATIENT_MANAGERS = [
        "care_team",
        "allergies",
        "care_plans",
        "medications",
        "medical_orders",
        "insurance_info",
        "advance_directives",
        "family_history",
        "medical_devices",
        "clinical_notes",
    ]

    @staticmethod
    def find_potential_duplicates(
        patient: Patient,
        similarity_threshold: float = 0.85,
    ) -> List[Tuple[Patient, float, Dict[str, Any]]]:
        candidates = Patient.objects.filter(is_active=True).exclude(id=patient.id)

        if patient.date_of_birth:
            candidates = candidates.filter(
                date_of_birth__range=(
                    patient.date_of_birth - timedelta(days=365),
                    patient.date_of_birth + timedelta(days=365),
                )
            )

        duplicates = []
        for candidate in candidates:
            score, details = DuplicatePatientDetector._calculate_similarity(patient, candidate)
            if score >= similarity_threshold:
                duplicates.append((candidate, score, details))

        duplicates.sort(key=lambda item: item[1], reverse=True)
        return duplicates

    @staticmethod
    def _calculate_similarity(patient1: Patient, patient2: Patient) -> Tuple[float, Dict[str, Any]]:
        first_name_sim = SequenceMatcher(
            None,
            patient1.first_name.lower(),
            patient2.first_name.lower(),
        ).ratio()
        last_name_sim = SequenceMatcher(
            None,
            patient1.last_name.lower(),
            patient2.last_name.lower(),
        ).ratio()
        name_score = (first_name_sim + last_name_sim) / 2

        dob_score = 0.0
        dob_diff = None
        if patient1.date_of_birth and patient2.date_of_birth:
            dob_diff = abs((patient1.date_of_birth - patient2.date_of_birth).days)
            if dob_diff == 0:
                dob_score = 1.0
            elif dob_diff <= 7:
                dob_score = 0.9
            elif dob_diff <= 30:
                dob_score = 0.7
            elif dob_diff <= 365:
                dob_score = 0.3

        phone_score = 0.0
        phone1 = PatientSearchService.normalize_phone(patient_phone(patient1))
        phone2 = PatientSearchService.normalize_phone(patient_phone(patient2))
        if phone1 and phone2:
            if phone1 == phone2:
                phone_score = 1.0
            elif len(phone1) >= 7 and len(phone2) >= 7 and phone1[-7:] == phone2[-7:]:
                phone_score = 0.8

        email_score = 0.0
        if patient_email(patient1) and patient_email(patient2):
            email_score = 1.0 if patient_email(patient1).lower() == patient_email(patient2).lower() else 0.0

        sex_score = 1.0 if _normalize_sex(patient1.sex) == _normalize_sex(patient2.sex) else 0.0
        mrn_score = 1.0 if patient1.medical_record_number and patient1.medical_record_number == patient2.medical_record_number else 0.0

        component_scores = {
            "name": name_score,
            "dob": dob_score,
            "phone": phone_score,
            "email": email_score,
            "sex": sex_score,
            "mrn": mrn_score,
        }
        total_score = (
            name_score * 0.35
            + dob_score * 0.30
            + phone_score * 0.12
            + email_score * 0.10
            + sex_score * 0.03
            + mrn_score * 0.10
        )

        return total_score, {
            "first_name_match": first_name_sim,
            "last_name_match": last_name_sim,
            "dob_difference_days": dob_diff,
            "phone_match": phone_score > 0,
            "email_match": email_score > 0,
            "sex_match": sex_score > 0,
            "mrn_match": mrn_score > 0,
            "component_scores": component_scores,
            "total_score": total_score,
        }

    @staticmethod
    def merge_patients(
        primary_patient: Patient,
        duplicate_patient: Patient,
        user: User,
    ) -> Dict[str, Any]:
        merge_results = {
            "primary_patient_id": primary_patient.id,
            "duplicate_patient_id": duplicate_patient.id,
            "merged_at": timezone.now(),
            "merged_by": user.id,
            "merged_data": {},
        }

        for manager_name in DuplicatePatientDetector.RELATED_PATIENT_MANAGERS:
            manager = getattr(duplicate_patient, manager_name, None)
            if manager is None:
                continue
            moved = 0
            for obj in manager.all():
                obj.patient = primary_patient
                update_fields = ["patient"]
                if hasattr(obj, "updated_by"):
                    obj.updated_by = user
                    update_fields.append("updated_by")
                if hasattr(obj, "updated_at"):
                    update_fields.append("updated_at")
                obj.save(update_fields=update_fields)
                moved += 1
            if moved:
                merge_results["merged_data"][manager_name] = moved

        # Practitioner links have a uniqueness constraint and need a deliberate
        # conflict policy, so this merge path leaves them untouched for review.
        if hasattr(duplicate_patient, "practitioner_links") and duplicate_patient.practitioner_links.exists():
            merge_results["merged_data"]["skipped_practitioner_links"] = duplicate_patient.practitioner_links.count()

        updated_fields: List[str] = []
        for field in [
            "medical_record_number",
            "middle_name",
            "name_suffix",
            "previous_name",
            "phone_number",
            "phone_number_type",
            "email_address",
            "current_address_line1",
            "current_address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "preferred_language",
            "occupation",
            "occupation_industry",
        ]:
            _copy_if_blank(primary_patient, duplicate_patient, field, updated_fields)

        if updated_fields:
            primary_patient.updated_by = user
            primary_patient.save(update_fields=updated_fields + ["updated_at", "updated_by"])
            merge_results["merged_data"]["updated_fields"] = updated_fields

        duplicate_patient.is_active = False
        duplicate_patient.updated_by = user
        duplicate_patient.save(update_fields=["is_active", "updated_at", "updated_by"])

        PatientDocument.objects.create(
            patient=primary_patient,
            note_type="progress",
            content=(
                f"Patient {patient_display_name(duplicate_patient)} "
                f"(ID: {duplicate_patient.id}) merged into this record."
            ),
            created_by=user,
        )

        return merge_results


class PatientDataValidator:
    """Validate and normalize patient data accepted by commands/importers."""

    @staticmethod
    def _canonicalize_input(data: Dict[str, Any]) -> Dict[str, Any]:
        canonical = dict(data or {})

        if "gender" in canonical and "sex" not in canonical:
            canonical["sex"] = canonical["gender"]
        if "email" in canonical and "email_address" not in canonical:
            canonical["email_address"] = canonical["email"]
        for phone_key in ("phone_mobile", "phone_home", "phone_work"):
            if phone_key in canonical and "phone_number" not in canonical:
                canonical["phone_number"] = canonical[phone_key]
        if "address_street" in canonical and "current_address_line1" not in canonical:
            canonical["current_address_line1"] = canonical["address_street"]
        if "address_city" in canonical and "city" not in canonical:
            canonical["city"] = canonical["address_city"]
        if "address_state" in canonical and "state" not in canonical:
            canonical["state"] = canonical["address_state"]
        if "address_zip" in canonical and "postal_code" not in canonical:
            canonical["postal_code"] = canonical["address_zip"]

        return canonical

    @staticmethod
    def validate_patient_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        data = PatientDataValidator._canonicalize_input(data)
        errors = []

        for field in ["first_name", "last_name", "date_of_birth", "sex"]:
            if not data.get(field):
                errors.append(f'{field.replace("_", " ").title()} is required')

        dob = _normalize_date(data.get("date_of_birth"))
        if data.get("date_of_birth") and not dob:
            errors.append("Invalid date of birth format (use YYYY-MM-DD)")
        elif dob:
            if dob > timezone.now().date():
                errors.append("Date of birth cannot be in the future")
            age = (timezone.now().date() - dob).days / 365.25
            if age > 150:
                errors.append("Date of birth indicates age over 150 years")

        if data.get("phone_number"):
            normalized = PatientSearchService.normalize_phone(data["phone_number"])
            if len(normalized) < 7:
                errors.append("Phone number must contain at least 7 digits")

        if data.get("email_address"):
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, str(data["email_address"])):
                errors.append("Invalid email format")

        if data.get("sex") and _normalize_sex(data["sex"]) not in {"M", "F", "O", "U"}:
            errors.append("Invalid sex value")

        return len(errors) == 0, errors

    @staticmethod
    def normalize_patient_data(data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = PatientDataValidator._canonicalize_input(data)

        for field in ["first_name", "last_name", "middle_name"]:
            if normalized.get(field):
                normalized[field] = str(normalized[field]).strip()

        if normalized.get("sex"):
            normalized["sex"] = _normalize_sex(normalized["sex"])

        if normalized.get("phone_number"):
            normalized["phone_number"] = re.sub(r"[^\d+\-()\s]", "", str(normalized["phone_number"])).strip()

        if normalized.get("email_address"):
            normalized["email_address"] = str(normalized["email_address"]).strip().lower()

        for field in ["current_address_line1", "current_address_line2", "city", "state", "postal_code"]:
            if normalized.get(field):
                normalized[field] = str(normalized[field]).strip()

        allowed_fields = {
            "first_name",
            "last_name",
            "middle_name",
            "date_of_birth",
            "sex",
            "phone_number",
            "phone_number_type",
            "email_address",
            "current_address_line1",
            "current_address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "medical_record_number",
        }
        return {key: value for key, value in normalized.items() if key in allowed_fields}


class PatientStatsService:
    """Generate patient statistics and dashboard summaries."""

    @staticmethod
    def get_patient_demographics() -> Dict[str, Any]:
        total_patients = Patient.objects.filter(is_active=True).count()
        sex_stats = Patient.objects.filter(is_active=True).values("sex").annotate(count=Count("id"))

        current_date = timezone.now().date()
        age_groups = {
            "Under 18": 0,
            "18-34": 0,
            "35-49": 0,
            "50-64": 0,
            "65+": 0,
        }

        for patient in Patient.objects.filter(is_active=True, date_of_birth__isnull=False):
            age = current_date.year - patient.date_of_birth.year - (
                (current_date.month, current_date.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
            )
            if age < 18:
                age_groups["Under 18"] += 1
            elif age < 35:
                age_groups["18-34"] += 1
            elif age < 50:
                age_groups["35-49"] += 1
            elif age < 65:
                age_groups["50-64"] += 1
            else:
                age_groups["65+"] += 1

        from django.db.models.functions import TruncMonth

        registration_stats = (
            Patient.objects.filter(is_active=True, created_at__gte=timezone.now() - timedelta(days=365))
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        return {
            "total_patients": total_patients,
            "sex_distribution": {item["sex"] or "U": item["count"] for item in sex_stats},
            "gender_distribution": {item["sex"] or "U": item["count"] for item in sex_stats},
            "age_distribution": age_groups,
            "registration_trends": list(registration_stats),
        }

    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        total_patients = Patient.objects.filter(is_active=True).count()
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_this_month = Patient.objects.filter(created_at__gte=current_month_start, is_active=True).count()

        return {
            "total_patients": total_patients,
            "active_patients": total_patients,
            "new_this_month": new_this_month,
            "potential_duplicates": 0,
        }


class EnhancedPatientService:
    """Compatibility facade for older callers that still import this service."""

    @staticmethod
    def get_patient_balance(patient_id: str) -> Decimal:
        # Billing is archived and not part of the active product core.
        return Decimal("0.00")

    @staticmethod
    def is_patient_deceased(patient_id: str) -> bool:
        try:
            patient = Patient.objects.get(id=patient_id)
            return patient.status == "deceased" or patient.date_of_death is not None
        except Patient.DoesNotExist:
            return False

    @staticmethod
    def advanced_patient_search(search_params: Dict[str, Any]):
        queryset = Patient.objects.filter(is_active=True)

        if search_params.get("name"):
            name = search_params["name"]
            queryset = queryset.filter(
                Q(first_name__icontains=name)
                | Q(last_name__icontains=name)
                | Q(middle_name__icontains=name)
            )

        if search_params.get("date_of_birth"):
            dob = _normalize_date(search_params["date_of_birth"])
            if dob:
                queryset = queryset.filter(date_of_birth=dob)

        if search_params.get("phone"):
            phone = PatientSearchService.normalize_phone(search_params["phone"])
            queryset = queryset.filter(phone_number__icontains=phone or search_params["phone"])

        if search_params.get("medical_record_number"):
            queryset = queryset.filter(medical_record_number__icontains=search_params["medical_record_number"])

        return queryset.order_by("last_name", "first_name")

    @staticmethod
    def detect_duplicate_patients(patient_data: Dict[str, Any]):
        normalized = PatientDataValidator.normalize_patient_data(patient_data)
        exact_matches = Patient.objects.filter(
            first_name__iexact=normalized.get("first_name", ""),
            last_name__iexact=normalized.get("last_name", ""),
            date_of_birth=normalized.get("date_of_birth"),
            is_active=True,
        )

        potential_duplicates = list(exact_matches)
        phone = normalized.get("phone_number")
        if phone:
            potential_duplicates.extend(Patient.objects.filter(phone_number=phone, is_active=True))

        return list({patient.id: patient for patient in potential_duplicates}.values())


class InsuranceManagementService:
    """Small helper around the active InsuranceData model."""

    @staticmethod
    def create_insurance_data(patient_id: str, insurance_data: Dict[str, Any]):
        patient = Patient.objects.get(id=patient_id)
        return InsuranceData.objects.create(patient=patient, **insurance_data)

    @staticmethod
    def get_active_insurance(patient_id: str, insurance_type: str = None):
        queryset = InsuranceData.objects.filter(patient_id=patient_id, is_active=True, coverage_status="active")
        if insurance_type:
            queryset = queryset.filter(coverage_type=insurance_type)
        return queryset.order_by("coverage_type")


class PatientReportService:
    """Generate simple patient summaries from the active patient model."""

    @staticmethod
    def generate_patient_summary_report(patient_id: str) -> Dict[str, Any]:
        patient = Patient.objects.get(id=patient_id)

        allergies = [
            {
                "substance": allergy.substance,
                "reaction": allergy.reaction,
                "severity": allergy.severity,
            }
            for allergy in patient.allergies.filter(is_active=True)
        ]

        medications = [
            {
                "medication": medication.medication,
                "dose_unit_of_measure": medication.dose_unit_of_measure,
                "route_of_administration": medication.route_of_administration,
                "dispense_status": medication.dispense_status,
            }
            for medication in patient.medications.filter(is_active=True)
        ]

        return {
            "basic_info": {
                "patient_id": str(patient.id),
                "full_name": patient_display_name(patient),
                "medical_record_number": patient.medical_record_number,
                "date_of_birth": str(patient.date_of_birth),
                "age": patient.age,
                "sex": patient.sex,
                "status": patient.status,
                "contact_info": {
                    "phone_number": patient.phone_number,
                    "email_address": patient.email_address,
                    "address": {
                        "line1": patient.current_address_line1,
                        "line2": patient.current_address_line2,
                        "city": patient.city,
                        "state": patient.state,
                        "postal_code": patient.postal_code,
                        "country": patient.country,
                    },
                },
            },
            "allergies": allergies,
            "current_medications": medications,
            "financial_balance": float(EnhancedPatientService.get_patient_balance(patient_id)),
            "generated_at": timezone.now().isoformat(),
        }
