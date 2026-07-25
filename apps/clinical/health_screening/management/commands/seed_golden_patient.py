from django.core.management.base import BaseCommand, CommandError

from apps.clinical.health_screening.golden_patient import (
    GoldenPatientError,
    GoldenPatientSeeder,
    GoldenPatientVerifier,
)


class Command(BaseCommand):
    help = (
        "Idempotently persist the synthetic golden conformance patient. "
        "Use --verify to run DB -> mapping -> all risk algorithms -> FHIR/Provenance."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify",
            action="store_true",
            help=(
                "Run the complete risk/FHIR conformance gate after seeding. "
                "The command exits non-zero if any invariant fails."
            ),
        )

    def handle(self, *args, **options):
        try:
            seeded = GoldenPatientSeeder().seed()
            self.stdout.write(
                self.style.SUCCESS(
                    "Golden patient seeded: "
                    f"patient_id={seeded.patient_id}, "
                    f"observations={seeded.observation_count}, "
                    f"questionnaire_responses={seeded.questionnaire_response_count}, "
                    f"input_fhir_resources={seeded.input_fhir_resource_count}."
                )
            )
            if options["verify"]:
                verified = GoldenPatientVerifier().verify(seeded.patient_id)
                self.stdout.write(
                    self.style.SUCCESS(
                        "Golden patient verification PASS: "
                        f"risk_run_id={verified.risk_run_id}, "
                        f"algorithms={verified.algorithm_count}, "
                        f"RiskAssessment={verified.risk_assessment_count}, "
                        f"result_Observation={verified.result_observation_count}, "
                        f"Provenance={verified.provenance_count}, "
                        f"basis_references={verified.basis_reference_count}."
                    )
                )
        except GoldenPatientError as exc:
            raise CommandError(f"Golden patient verification failed: {exc}") from exc
