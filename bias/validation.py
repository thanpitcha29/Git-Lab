"""Parse and validate raw form input. No Flask imports here."""

import math
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

FIELDS = ("VCC", "R1", "R2", "RC", "RE", "beta", "VBE")

_POSITIVE = {
    "VCC": "VCC must be greater than 0 V",
    "R1": "R1 must be greater than 0 Ω",
    "R2": "R2 must be greater than 0 Ω",
    "RE": "RE must be greater than 0 Ω (the model needs an emitter resistor)",
    "beta": "beta must be greater than 0",
}

_NON_NEGATIVE = {
    "RC": "RC must be 0 Ω or greater",
    "VBE": "VBE must be 0 V or greater",
}


@dataclass(frozen=True)
class Inputs:
    VCC: float
    R1: float
    R2: float
    RC: float
    RE: float
    beta: float
    VBE: float


def parse_inputs(form: Mapping[str, str]) -> Tuple[Optional[Inputs], list]:
    """Return (Inputs, []) when every field is valid, else (None, errors)."""
    values = {}
    errors = []

    for name in FIELDS:
        raw = form.get(name)
        if raw is None or str(raw).strip() == "":
            errors.append(f"{name} must be a number")
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            errors.append(f"{name} must be a number")
            continue
        if not math.isfinite(value):
            errors.append(f"{name} must be a finite number")
            continue
        values[name] = value

    for name in FIELDS:
        if name not in values:
            continue
        value = values[name]
        if name in _POSITIVE and value <= 0:
            errors.append(_POSITIVE[name])
        elif name in _NON_NEGATIVE and value < 0:
            errors.append(_NON_NEGATIVE[name])

    if errors:
        return None, errors
    return Inputs(**values), []
