"""DC bias calculations for an NPN common-emitter stage.

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


def _delta_pct(value: float, reference: float) -> Optional[float]:
    if reference == 0:
        return None
    return abs(value - reference) / abs(reference) * 100.0


def compare(exact: OperatingPoint, approx: OperatingPoint,
            beta: float, RE: float, R2: float) -> Comparison:
    ratio = beta * RE / R2
    rule_satisfied = ratio >= 10.0
    valid = (rule_satisfied
             and exact.region == "active"
             and approx.region == "active")
    return Comparison(
        approx=approx,
        delta_ic_pct=_delta_pct(approx.IC, exact.IC),
        delta_vce_pct=_delta_pct(approx.VCE, exact.VCE),
        beta_re_over_r2=ratio,
        rule_satisfied=rule_satisfied,
        approximation_valid=valid,
    )
