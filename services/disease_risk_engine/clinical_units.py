"""Strict canonical-unit boundary for disease-risk Observation inputs.

Only explicitly listed, dimensionally compatible units are accepted.  The
module performs deterministic unit conversion; it never guesses a unit,
clamps a clinical value, or treats a missing unit as canonical.  Legacy typed
schema fields can opt into :func:`assume_legacy_canonical_quantity` at their
repository boundary, where that assumption is recorded in provenance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping, Optional

from .algorithm_registry import CLINICAL_VARIABLES


class UnitContractError(ValueError):
    """Raised when code requests a field without a declared unit contract."""


@dataclass(frozen=True, slots=True)
class UnitTransform:
    multiplier: float
    code: str


@dataclass(frozen=True, slots=True)
class ObservationUnitContract:
    field: str
    canonical_unit: str
    transforms: Mapping[str, UnitTransform]

    def normalize(self, value: Any, unit: Any) -> Optional["NormalizedClinicalQuantity"]:
        numeric = _finite_non_negative_number(value)
        unit_text = str(unit or "").strip()
        if numeric is None or not unit_text:
            return None
        transform = self.transforms.get(_unit_token(unit_text))
        if transform is None:
            return None
        normalized = numeric * transform.multiplier
        if not math.isfinite(normalized) or normalized < 0:
            return None
        return NormalizedClinicalQuantity(
            value=round(normalized, 6),
            original_unit=unit_text,
            normalized_unit=self.canonical_unit,
            conversion=transform.code,
        )


@dataclass(frozen=True, slots=True)
class NormalizedClinicalQuantity:
    value: float
    original_unit: str
    normalized_unit: str
    conversion: str


def _unit_token(unit: str) -> str:
    return (
        str(unit)
        .strip()
        .replace("µ", "u")
        .replace("μ", "u")
        .replace("²", "2")
        .replace(" ", "")
        .casefold()
    )


def _finite_non_negative_number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return numeric if math.isfinite(numeric) and numeric >= 0 else None


def _canonical_unit(field: str, fallback: Optional[str] = None) -> str:
    registry_contract = CLINICAL_VARIABLES.get(field)
    if registry_contract is not None and registry_contract.unit:
        return registry_contract.unit
    if fallback:
        return fallback
    raise UnitContractError(f"Observation field {field!r} has no canonical unit")


def _rule(
    field: str,
    *,
    fallback_unit: Optional[str] = None,
    identity_units: tuple[str, ...],
    conversions: Mapping[str, tuple[float, str]] = MappingProxyType({}),
) -> ObservationUnitContract:
    transforms: dict[str, UnitTransform] = {
        _unit_token(unit): UnitTransform(1.0, "identity") for unit in identity_units
    }
    for unit, (multiplier, code) in conversions.items():
        token = _unit_token(unit)
        if token in transforms:
            raise UnitContractError(f"Unit {unit!r} is declared twice for {field!r}")
        transforms[token] = UnitTransform(multiplier, code)
    return ObservationUnitContract(
        field=field,
        canonical_unit=_canonical_unit(field, fallback_unit),
        transforms=MappingProxyType(transforms),
    )


_LENGTH_CONVERSIONS = MappingProxyType(
    {
        "m": (100.0, "m_to_cm"),
        "meter": (100.0, "m_to_cm"),
        "meters": (100.0, "m_to_cm"),
        "metre": (100.0, "m_to_cm"),
        "metres": (100.0, "m_to_cm"),
    }
)
_CHOLESTEROL_CONVERSIONS = MappingProxyType(
    {"mmol/L": (38.66976, "cholesterol_mmol_per_l_to_mg_per_dl")}
)

_UNIT_CONTRACTS = (
    _rule(
        "body_height",
        fallback_unit="cm",
        identity_units=("cm", "centimeter", "centimeters", "centimetre", "centimetres"),
        conversions=_LENGTH_CONVERSIONS,
    ),
    _rule(
        "body_weight",
        fallback_unit="kg",
        identity_units=("kg", "kilogram", "kilograms"),
    ),
    _rule(
        "bmi",
        identity_units=("kg/m2", "kg/m^2", "kg/m²"),
    ),
    _rule(
        "waist_circumference",
        identity_units=("cm", "centimeter", "centimeters", "centimetre", "centimetres"),
        conversions=_LENGTH_CONVERSIONS,
    ),
    _rule(
        "hip_circumference",
        fallback_unit="cm",
        identity_units=("cm", "centimeter", "centimeters", "centimetre", "centimetres"),
        conversions=_LENGTH_CONVERSIONS,
    ),
    _rule(
        "alcohol_drinks_per_week",
        identity_units=("1/wk", "{drink}/wk", "drink/week", "drinks/week"),
    ),
    _rule(
        "heart_rate",
        fallback_unit="/min",
        identity_units=("/min", "beat/min", "beats/min", "{beats}/min"),
    ),
    _rule(
        "resting_heart_rate",
        identity_units=("/min", "beat/min", "beats/min", "{beats}/min"),
    ),
    _rule(
        "systolic_bp",
        identity_units=("mm[Hg]", "mmHg"),
    ),
    _rule(
        "diastolic_bp",
        identity_units=("mm[Hg]", "mmHg"),
    ),
    _rule(
        "fasting_glucose",
        identity_units=("mg/dL",),
        conversions=MappingProxyType(
            {"mmol/L": (18.01559, "glucose_mmol_per_l_to_mg_per_dl")}
        ),
    ),
    _rule(
        "total_cholesterol",
        identity_units=("mg/dL",),
        conversions=_CHOLESTEROL_CONVERSIONS,
    ),
    _rule(
        "hdl_cholesterol",
        identity_units=("mg/dL",),
        conversions=_CHOLESTEROL_CONVERSIONS,
    ),
    _rule(
        "triglycerides",
        identity_units=("mg/dL",),
        conversions=MappingProxyType(
            {"mmol/L": (88.57, "triglyceride_mmol_per_l_to_mg_per_dl")}
        ),
    ),
    _rule(
        "creatinine",
        fallback_unit="mg/dL",
        identity_units=("mg/dL",),
        conversions=MappingProxyType(
            {
                "umol/L": (1.0 / 88.4, "creatinine_umol_per_l_to_mg_per_dl"),
                "micromol/L": (1.0 / 88.4, "creatinine_umol_per_l_to_mg_per_dl"),
            }
        ),
    ),
    _rule(
        "egfr",
        identity_units=(
            "mL/min/{1.73_m2}",
            "mL/min/1.73m2",
            "mL/min/1.73 m2",
        ),
    ),
    _rule("alt_gpt", identity_units=("U/L", "IU/L", "[IU]/L")),
    _rule("ast_got", identity_units=("U/L", "IU/L", "[IU]/L")),
    _rule("ast_uln", identity_units=("U/L", "IU/L", "[IU]/L")),
    _rule("ggt", identity_units=("U/L", "IU/L", "[IU]/L")),
    _rule("ggt_uln", identity_units=("U/L", "IU/L", "[IU]/L")),
    _rule(
        "platelet_count",
        identity_units=("10*9/L", "10^9/L", "10*3/uL", "10^3/uL", "K/uL"),
    ),
    _rule(
        "albumin",
        identity_units=("g/dL",),
        conversions=MappingProxyType({"g/L": (0.1, "albumin_g_per_l_to_g_per_dl")}),
    ),
    _rule(
        "insulin",
        identity_units=("u[IU]/mL", "[uIU]/mL", "uIU/mL"),
    ),
    _rule("rdw", identity_units=("%",)),
    _rule("mean_platelet_volume", identity_units=("fL",)),
    _rule("hba1c", identity_units=("%",)),
    _rule("hs_crp", identity_units=("mg/L",)),
    _rule("microalbumin_excretion_rate", identity_units=("ug/min", "mcg/min")),
    _rule("pulmonary_nodule_diameter", identity_units=("mm",)),
    _rule(
        "urine_albumin_creatinine_ratio",
        fallback_unit="mg/g",
        identity_units=("mg/g", "mg/g{creat}", "mg/g creatinine"),
    ),
    _rule(
        "apoe_e4",
        identity_units=("{allele}", "allele", "alleles"),
    ),
)

OBSERVATION_UNIT_CONTRACTS: Mapping[str, ObservationUnitContract] = MappingProxyType(
    {contract.field: contract for contract in _UNIT_CONTRACTS}
)

if len(OBSERVATION_UNIT_CONTRACTS) != len(_UNIT_CONTRACTS):
    raise UnitContractError("Duplicate Observation unit-contract field")


def canonical_unit_for(field: str) -> str:
    try:
        return OBSERVATION_UNIT_CONTRACTS[field].canonical_unit
    except KeyError as exc:
        raise UnitContractError(f"Observation field {field!r} has no unit contract") from exc


def normalize_observation_quantity(
    field: str,
    value: Any,
    unit: Any,
) -> Optional[NormalizedClinicalQuantity]:
    try:
        contract = OBSERVATION_UNIT_CONTRACTS[field]
    except KeyError as exc:
        raise UnitContractError(f"Observation field {field!r} has no unit contract") from exc
    return contract.normalize(value, unit)


def assume_legacy_canonical_quantity(
    field: str,
    value: Any,
) -> Optional[NormalizedClinicalQuantity]:
    """Accept a typed legacy-schema scalar under its documented field unit."""

    numeric = _finite_non_negative_number(value)
    if numeric is None:
        return None
    canonical_unit = canonical_unit_for(field)
    return NormalizedClinicalQuantity(
        value=round(numeric, 6),
        original_unit=canonical_unit,
        normalized_unit=canonical_unit,
        conversion="legacy_schema_contract",
    )


__all__ = [
    "NormalizedClinicalQuantity",
    "OBSERVATION_UNIT_CONTRACTS",
    "ObservationUnitContract",
    "UnitContractError",
    "assume_legacy_canonical_quantity",
    "canonical_unit_for",
    "normalize_observation_quantity",
]
