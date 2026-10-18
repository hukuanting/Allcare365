"""Composition of the user-attested expert source collection.

The expert attestation is accepted under the 2026-10-10 user instruction.
Executable definitions still need deterministic, complete equations; missing
source material is tracked separately and never replaced by a guessed score.
"""
from .expert_metabolic import DEFINITIONS as METABOLIC

from .expert_adapters import DEFINITIONS as ADAPTERS

DEFINITIONS = (*METABOLIC, *ADAPTERS)
