"""Parse and validate raw form input. No Flask imports here.

Each bias mode needs only its own fields; fields that do not belong to the
selected mode are ignored rather than reported as errors.
"""

import math
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

MODES = {
    "divider": ("VCC", "R1", "R2", "RC", "RE", "beta", "VBE"),
    "fixed": ("VCC", "RB", "RC", "beta", "VBE"),
    "emitter": ("VCC", "RB", "RC", "RE", "beta", "VBE"),
}

MODE_NAMES = {
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
    "divider": "Voltage Divider Bias",
}

_POSITIVE = {
    "VCC": "VCC must be greater than 0 V",
    "R1": "R1 must be greater than 0 \u03a9",
    "R2": "R2 must be greater than 0 \u03a9",
    "RB": "RB must be greater than 0 \u03a9",
    "RE": "RE must be greater than 0 \u03a9 (the model needs an emitter resistor)",
    "beta": "beta must be greater than 0",
}

_NON_NEGATIVE = {
    "RC": "RC must be 0 \u03a9 or greater",
    "VBE": "VBE must be 0 V or greater",
}


@dataclass(frozen=True)
class Inputs:
    VCC: float
    RC: float
    beta: float
    VBE: float
    R1: Optional[float] = None
    R2: Optional[float] = None
    RE: Optional[float] = None
    RB: Optional[float] = None


def validate_mode(mode: Optional[str]) -> Optional[str]:
    """Return the mode when it is known, otherwise None."""
    if mode in MODES:
        return mode
    return None


def unknown_mode_error(mode: Optional[str]) -> str:
    return (f"Unknown bias mode '{mode}'. "
            "Choose fixed, emitter or divider.")


def parse_inputs(form: Mapping[str, str], mode: str = "divider"
                 ) -> Tuple[Optional[Inputs], list]:
    """Return (Inputs, []) when the mode's fields are valid, else (None, errors)."""
    fields = MODES.get(mode)
    if fields is None:
        return None, [unknown_mode_error(mode)]

    values = {}
    errors = []

    for name in fields:
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

    for name in fields:
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
