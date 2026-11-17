"""DC bias calculations for three NPN common-emitter topologies.

Pure engineering logic: this module must never import Flask or Jinja.
"""

from dataclasses import dataclass
from typing import Optional

VCE_SAT = 0.2  # V, collector-emitter saturation threshold


@dataclass(frozen=True)
class OperatingPoint:
    VBB: float
    RB: float
    IB: float
    IC: float
    IE: float
    VE: float
    VB: float
    VC: float
    VCE: float
    region: str
    IC_sat: Optional[float] = None


@dataclass(frozen=True)
class Comparison:
    approx: OperatingPoint
    delta_ic_pct: Optional[float]
    delta_vce_pct: Optional[float]
    beta_re_over_r2: float
    rule_satisfied: bool
    approximation_valid: bool
    invalid_reason: Optional[str] = None


def _regions(VCC: float, RC: float, RE: float, VCE: float) -> tuple:
    if VCE < VCE_SAT:
        return "saturation", (VCC - VCE_SAT) / (RC + RE)
    return "active", None


def solve_exact(VCC: float, R1: float, R2: float, RC: float,
                RE: float, beta: float, VBE: float) -> OperatingPoint:
    """Exact base-loop solution: VBB = IB*RB + VBE + IE*RE."""
    VBB = VCC * R2 / (R1 + R2)
    RB = R1 * R2 / (R1 + R2)

    if VBB <= VBE:
        return OperatingPoint(
            VBB=VBB, RB=RB, IB=0.0, IC=0.0, IE=0.0,
            VE=0.0, VB=VBB, VC=VCC, VCE=VCC, region="cutoff",
        )

    IB = (VBB - VBE) / (RB + (1 + beta) * RE)
    IC = beta * IB
    IE = (1 + beta) * IB
    VE = IE * RE
    VB = VE + VBE
    VC = VCC - IC * RC
    VCE = VC - VE
    region, IC_sat = _regions(VCC, RC, RE, VCE)

    return OperatingPoint(
        VBB=VBB, RB=RB, IB=IB, IC=IC, IE=IE,
        VE=VE, VB=VB, VC=VC, VCE=VCE, region=region, IC_sat=IC_sat,
    )


def solve_approximate(VCC: float, R1: float, R2: float, RC: float,
                      RE: float, beta: float, VBE: float) -> OperatingPoint:
    """Independent check: stiff divider, IB neglected, beta never used."""
    VBB = VCC * R2 / (R1 + R2)
    RB = R1 * R2 / (R1 + R2)

    if VBB <= VBE:
        return OperatingPoint(
            VBB=VBB, RB=RB, IB=0.0, IC=0.0, IE=0.0,
            VE=0.0, VB=VBB, VC=VCC, VCE=VCC, region="cutoff",
        )

    VB = VBB
    VE = VB - VBE
    IE = VE / RE
    IC = IE
    VC = VCC - IC * RC
    VCE = VC - VE
    region, IC_sat = _regions(VCC, RC, RE, VCE)

    return OperatingPoint(
        VBB=VBB, RB=RB, IB=0.0, IC=IC, IE=IE,
        VE=VE, VB=VB, VC=VC, VCE=VCE, region=region, IC_sat=IC_sat,
    )


def compare(exact: OperatingPoint, approx: OperatingPoint,
            beta: float, RE: float, R2: float) -> Comparison:
    ratio = beta * RE / R2
    rule_satisfied = ratio >= 10.0
    if exact.region != "active":
        reason = "outside_active_region"
    elif approx.region != "active":
        reason = "approximate_saturation"
    elif not rule_satisfied:
        reason = "divider_not_stiff"
    else:
        reason = None

    return Comparison(
        approx=approx,
        delta_ic_pct=_delta_pct(approx.IC, exact.IC),
        delta_vce_pct=_delta_pct(approx.VCE, exact.VCE),
        beta_re_over_r2=ratio,
        rule_satisfied=rule_satisfied,
        approximation_valid=reason is None,
        invalid_reason=reason,
    )


def _delta_pct(value: float, reference: float) -> Optional[float]:
    if reference == 0:
        return None
    return abs(value - reference) / abs(reference) * 100.0


# ---------------------------------------------------------------------------
# Lab 03: one canonical result shape for all three topologies.
# ---------------------------------------------------------------------------

CUTOFF_WARNING = (
    "IB <= 0: the base-emitter junction is not forward biased, so the "
    "Forward Active model does not apply here."
)


def _warning_for(region: str, vce: float) -> Optional[str]:
    if region == "cutoff":
        return CUTOFF_WARNING
    if region == "saturation":
        return (f"VCE = {vce:.3f} V <= {VCE_SAT} V: the transistor is in "
                "saturation, so the Forward Active model does not apply here.")
    return None


def _point(mode: str, VCC: float, RC: float, RE: float, VBE: float,
           beta: float, IB: float, ve, vth: Optional[float] = None,
           rth: Optional[float] = None) -> dict:
    """Shared finishing step: IB -> IC, IE, VB, VE, VC, VCE.

    `ve` is None when VE must be computed as IE*RE (emitter and divider),
    and 0.0 for fixed bias where the emitter is grounded.
    """
    if IB <= 0:
        return {
            "mode": mode, "ib_ma": 0.0, "ib_ua": 0.0, "ic_ma": 0.0,
            "ie_ma": 0.0, "vb_v": VBE, "ve_v": 0.0, "vc_v": VCC,
            "vce_v": VCC, "vth_v": vth, "rth_ohm": rth,
            "region": "cutoff", "ic_sat_ma": None,
            "warning": CUTOFF_WARNING,
        }

    IC = beta * IB
    IE = (1 + beta) * IB
    VE = IE * RE if ve is None else ve
    VB = VE + VBE
    VC = VCC - IC * RC
    VCE = VC - VE
    region, IC_sat = _regions(VCC, RC, RE, VCE)

    return {
        "mode": mode,
        "ib_ma": IB * 1000.0, "ib_ua": IB * 1e6,
        "ic_ma": IC * 1000.0, "ie_ma": IE * 1000.0,
        "vb_v": VB, "ve_v": VE, "vc_v": VC, "vce_v": VCE,
        "vth_v": vth, "rth_ohm": rth,
        "region": region,
        "ic_sat_ma": None if IC_sat is None else IC_sat * 1000.0,
        "warning": _warning_for(region, VCE),
    }


def solve_fixed(VCC: float, RB: float, RC: float,
                beta: float, VBE: float) -> dict:
    """Fixed bias: IB = (VCC - VBE) / RB, emitter grounded (VE = 0)."""
    IB = (VCC - VBE) / RB
    return _point("fixed", VCC, RC, 0.0, VBE, beta, IB, 0.0)


def solve_emitter(VCC: float, RB: float, RC: float, RE: float,
                  beta: float, VBE: float) -> dict:
    """Emitter bias: IB = (VCC - VBE) / (RB + (beta + 1)*RE)."""
    IB = (VCC - VBE) / (RB + (1 + beta) * RE)
    return _point("emitter", VCC, RC, RE, VBE, beta, IB, None)


def solve_divider(VCC: float, R1: float, R2: float, RC: float,
                  RE: float, beta: float, VBE: float) -> dict:
    """Voltage divider bias, reusing the Lab 02 solver unchanged."""
    op = solve_exact(VCC, R1, R2, RC, RE, beta, VBE)
    return {
        "mode": "divider",
        "ib_ma": op.IB * 1000.0, "ib_ua": op.IB * 1e6,
        "ic_ma": op.IC * 1000.0, "ie_ma": op.IE * 1000.0,
        "vb_v": op.VB, "ve_v": op.VE, "vc_v": op.VC, "vce_v": op.VCE,
        "vth_v": op.VBB, "rth_ohm": op.RB,
        "region": op.region,
        "ic_sat_ma": None if op.IC_sat is None else op.IC_sat * 1000.0,
        "warning": _warning_for(op.region, op.VCE),
    }
