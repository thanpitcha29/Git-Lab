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

    if VCE < VCE_SAT:
        region = "saturation"
        IC_sat = (VCC - VCE_SAT) / (RC + RE)
    else:
        region = "active"
        IC_sat = None

    return OperatingPoint(
        VBB=VBB, RB=RB, IB=IB, IC=IC, IE=IE,
        VE=VE, VB=VB, VC=VC, VCE=VCE, region=region, IC_sat=IC_sat,
    )
