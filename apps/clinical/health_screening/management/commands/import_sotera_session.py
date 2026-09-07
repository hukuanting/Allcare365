import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.clinical.health_screening.sotera_research import (
    SoteraResearchSessionService,
)


class Command(BaseCommand):
    help = (
        "Inspect or import one confidential Sotera research session ZIP. "
        "The command is dry-run unless --commit is supplied."
    )

    def add_arguments(self, parser):
        parser.add_argument("archive_path", help="Path to one Sotera session ZIP")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Persist the pseudonymous session, observations, and quality analysis.",
        )
        parser.add_argument(
            "--skip-crc",
            action="store_true",
            help="Skip the full ZIP CRC check. SHA-256 and schema checks still run.",
        )
        parser.add_argument(
            "--allow-remote-database",
            action="store_true",
            help=(
                "Allow a commit to a non-local database. Use only after confirming "
                "the data-use agreement and hosting controls."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print the deidentified aggregate result as JSON.",
        )

    def handle(self, *args, **options):
        archive_path = Path(options["archive_path"]).resolve()
        try:
            result = SoteraResearchSessionService(
                archive_path,
                verify_crc=not options["skip_crc"],
            ).run(
                commit=options["commit"],
                allow_remote_database=options["allow_remote_database"],
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
            return

        mode = "COMMIT" if result["committed"] else "DRY-RUN"
        source = result["source"]
        session = result["session"]
        numeric = result["numeric_summary"]
        waveform = result["waveform_summary"]
        quality = result["quality"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Sotera {mode}: {source['session_pseudonym']} "
                f"duration={session['duration_hours']:.3f}h "
                f"quality={quality['status']}"
            )
        )
        self.stdout.write(
            "archive_sha256=" + source["archive_sha256"]
        )
        self.stdout.write(
            "numeric: "
            f"source_rows={numeric['source_rows']} "
            f"planned={numeric['planned_observations']} "
            f"excluded={numeric['excluded_rows']}"
        )
        for signal, details in numeric["signals"].items():
            self.stdout.write(
                f"  {signal:<10} rows={details['rows']:<7} "
                f"importable={details['importable_rows']:<7} "
                f"valid={details['valid_pct']}% "
                f"median={details['median']} {details['unit']}"
            )
        coverage = waveform["continuous_signal_coverage_pct"]
        self.stdout.write(
            "waveforms: "
            f"signals={len(waveform['signals'])} "
            f"raw_samples={waveform['raw_samples']} "
            f"coverage_median={coverage['median']}% "
            "raw_samples_imported=false"
        )
        self.stdout.write(
            "calibration: "
            f"events={result['calibration_summary']['events']} "
            f"quality={result['calibration_summary']['quality_counts']}"
        )
        for finding in quality["findings"]:
            self.stdout.write(self.style.WARNING(f"finding: {finding}"))

        if result["committed"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"batch={result['batch_id']} patient={result['patient_id']} "
                    f"analysis_job={result['analysis_job_id']} "
                    f"observations={result['imported_observations']} "
                    f"idempotent={result['idempotent']}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run only; rerun with --commit to write to the local database."
                )
            )
