"""ngspice adapter for the CE voltage-divider reference circuit.

Owns four things and nothing else: input validation for the SPICE form,
netlist generation, running ngspice as an external process, and parsing the
ASCII data files ngspice writes back.

No Flask imports. Every run gets a fresh working directory under ``runs/``
so two browser requests can never overwrite each other's log or data file.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Mapping, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "runs"

# Stand-in model card: the instructor starter kit was not provided, so the
# netlist carries an explicit, documented 2N3904 card instead of guessing a
# device. Replace it if the course supplies its own model.
MODEL_NAME = "2N3904"
MODEL_CARD = (
    ".model Q2N3904 NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 "
    "ISE=6.734f IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 "
    "CJC=3.638p MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 VJE=.75 "
    "TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)"
)

ANALYSES = ("dc", "ac", "tran")
ANALYSIS_NAMES = {
    "dc": "DC operating point (.op)",
    "ac": "AC sweep (.ac)",
    "tran": "Transient (.tran)",
}

# SPICE form fields: resistors in kOhm, capacitors in uF, amplitude in mV.
SIM_FIELDS = (
    ("VCC", "VCC (Supply)", "V"),
    ("R1", "R1 (Upper Divider)", "k\u03a9"),
    ("R2", "R2 (Lower Divider)", "k\u03a9"),
    ("RC", "RC (Collector)", "k\u03a9"),
    ("RE", "RE (Emitter)", "k\u03a9"),
    ("RL", "RL (Load)", "k\u03a9"),
    ("CIN", "Cin (Input Coupling)", "\u00b5F"),
    ("COUT", "Cout (Output Coupling)", "\u00b5F"),
    ("amp_mv", "Source Amplitude", "mV"),
    ("freq_hz", "Source Frequency", "Hz"),
)

SIM_DEFAULTS = {
    "VCC": "12", "R1": "100", "R2": "22", "RC": "2.2", "RE": "1.0",
    "RL": "10", "CIN": "10", "COUT": "10", "amp_mv": "10", "freq_hz": "1000",
}

_POSITIVE = {
    "VCC": "VCC must be greater than 0 V",
    "R1": "R1 must be greater than 0 \u03a9",
    "R2": "R2 must be greater than 0 \u03a9",
    "RC": "RC must be greater than 0 \u03a9",
    "RE": "RE must be greater than 0 \u03a9",
    "RL": "RL must be greater than 0 \u03a9",
    "CIN": "Cin must be greater than 0 \u00b5F",
    "COUT": "Cout must be greater than 0 \u00b5F",
    "amp_mv": "Amplitude must be greater than 0 mV",
    "freq_hz": "Frequency must be greater than 0 Hz",
}

_LIMITS = {
    "freq_hz": (1.0, 10e6, "Frequency must be between 1 Hz and 10 MHz"),
    "amp_mv": (0.1, 1000.0, "Amplitude must be between 0.1 mV and 1000 mV"),
}

# ngspice AC sweep: wide enough to show the coupling high-pass corner
# (a few Hz with these values) and the 2N3904 high-frequency roll-off.
AC_START_HZ = 1.0
AC_STOP_HZ = 100e6
AC_POINTS_PER_DECADE = 20

# Transient: run long enough for the 10 uF coupling capacitors to settle,
# then plot only the final periods (see tran_window()).
TRAN_STOP_S = 0.2
TRAN_MIN_STEP_S = 1e-6
TRAN_MAX_STEP_S = 20e-6
TRAN_MAX_POINTS = 60_000

DEFAULT_TIMEOUT_S = 60.0


class SpiceError(Exception):
    """A simulation failure with a machine-readable kind and a short message."""

    def __init__(self, kind: str, message: str, detail: str = ""):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.detail = detail


def find_ngspice() -> Optional[Path]:
    """Locate the ngspice console binary, preferring the project-local copy."""
    candidates = []
    env = os.environ.get("NGSPICE_BIN")
    if env:
        candidates.append(Path(env))
    candidates.extend([
        PROJECT_ROOT / ".tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe",
        PROJECT_ROOT / ".tools" / "ngspice" / "Spice64" / "bin" / "ngspice.exe",
    ])
    for name in ("ngspice_con", "ngspice"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


_ENGINE_CACHE: Optional[dict] = None


def engine_info(refresh: bool = False) -> dict:
    """Return availability, path and version of the SPICE engine (cached)."""
    global _ENGINE_CACHE
    if _ENGINE_CACHE is not None and not refresh:
        return _ENGINE_CACHE

    exe = find_ngspice()
    info = {
        "available": False,
        "path": str(exe) if exe else "",
        "version": "",
        "model": MODEL_NAME,
        "model_note": ("2N3904 card embedded in spice_engine.py (stand-in; "
                       "replace with the course model if provided)"),
    }
    if exe:
        try:
            proc = subprocess.run(
                [str(exe), "-v"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=20, check=False,
            )
            match = re.search(r"ngspice-\d+(?:\.\d+)?", proc.stdout or "")
            info["version"] = match.group(0) if match else "ngspice (version unreadable)"
            info["available"] = True
        except (OSError, subprocess.SubprocessError):
            info["available"] = False
    _ENGINE_CACHE = info
    return info


def parse_params(form: Mapping[str, str]) -> Tuple[Optional[dict], list]:
    """Convert the SPICE form to SI units, returning (params, errors).

    The form uses kOhm, uF and mV; the netlist needs Ohm, F and V. Conversion
    happens exactly once, here, before validation.
    """
    errors = []
    values = {}

    for name, _label, _unit in SIM_FIELDS:
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
        if value <= 0:
            errors.append(_POSITIVE[name])
            continue
        if name in _LIMITS:
            low, high, message = _LIMITS[name]
            if not (low <= value <= high):
                errors.append(message)
                continue
        values[name] = value

    if errors:
        return None, errors

    params = {
        "VCC": values["VCC"],
        "R1": values["R1"] * 1e3,
        "R2": values["R2"] * 1e3,
        "RC": values["RC"] * 1e3,
        "RE": values["RE"] * 1e3,
        "RL": values["RL"] * 1e3,
        "CIN": values["CIN"] * 1e-6,
        "COUT": values["COUT"] * 1e-6,
        "amp": values["amp_mv"] * 1e-3,
        "freq": values["freq_hz"],
    }
    return params, []


def _fmt(value: float) -> str:
    return f"{value:.6g}"


def tran_timing(freq: float) -> Tuple[float, float]:
    """Return (step, stop) for the transient run in seconds."""
    period = 1.0 / freq
    step = min(period / 200.0, TRAN_MAX_STEP_S)
    step = max(step, TRAN_MIN_STEP_S, TRAN_STOP_S / TRAN_MAX_POINTS)
    return step, TRAN_STOP_S


def build_netlist(params: dict, analysis: str) -> str:
    """Build the CE voltage-divider netlist for one analysis."""
    if analysis not in ANALYSES:
        raise SpiceError("bad_analysis", f"Unknown analysis '{analysis}'.")

    lines = [
        "* ENG29 2121 Lab 04 - CE voltage-divider amplifier",
        f"* analysis={analysis} model={MODEL_NAME}",
        f"VCC vcc 0 {_fmt(params['VCC'])}",
        f"R1 vcc base {_fmt(params['R1'])}",
        f"R2 base 0 {_fmt(params['R2'])}",
        f"RC vcc coll {_fmt(params['RC'])}",
        f"RE emit 0 {_fmt(params['RE'])}",
        f"CIN src base {_fmt(params['CIN'])}",
        f"COUT coll out {_fmt(params['COUT'])}",
        f"RL out 0 {_fmt(params['RL'])}",
    ]
    if analysis == "tran":
        lines.append(
            f"VIN src 0 dc 0 sin(0 {_fmt(params['amp'])} {_fmt(params['freq'])})")
    else:
        lines.append("VIN src 0 dc 0 ac 1")
    lines.append("Q1 coll base emit Q2N3904")
    lines.append(MODEL_CARD)

    if analysis == "dc":
        lines.append(".op")
        lines.append(".control")
        lines.append("run")
        lines.append("wrdata op.txt v(base) v(coll) v(emit) v(vcc) "
                     "@q1[ic] @q1[ib] @q1[ie]")
    elif analysis == "ac":
        lines.append(f".ac dec {AC_POINTS_PER_DECADE} "
                     f"{_fmt(AC_START_HZ)} {_fmt(AC_STOP_HZ)}")
        lines.append(".control")
        lines.append("run")
        lines.append("wrdata ac.txt vdb(out) vp(out) vdb(src) vp(src)")
    else:
        step, stop = tran_timing(params["freq"])
        lines.append(f".tran {_fmt(step)} {_fmt(stop)}")
        lines.append(".control")
        lines.append("run")
        lines.append("wrdata tran.txt time v(src) v(out)")

    lines.extend([".endc", ".end", ""])
    return "\n".join(lines)


def parse_wrdata(path: Path) -> list:
    """Parse an ngspice wrdata file into rows of (scale, value) pairs.

    wrdata writes every requested vector as its own scale/value pair on the
    same line, so ``time v(src) v(out)`` becomes three pairs per line:
    ``(t, t) (t, vin) (t, vout)``. Keeping the row structure is what lets the
    parsers tell the vectors apart.
    """
    if not path.is_file() or path.stat().st_size == 0:
        raise SpiceError("empty_output", "ngspice produced no data file.")
    rows = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SpiceError("empty_output", "Could not read the data file.",
                         str(exc)) from exc
    for line in text.splitlines():
        numbers = []
        for token in line.split():
            try:
                numbers.append(float(token))
            except ValueError:
                numbers = []
                break
        if len(numbers) >= 2:
            rows.append([(numbers[i], numbers[i + 1])
                         for i in range(0, len(numbers) - 1, 2)])
    if not rows:
        raise SpiceError("empty_output", "ngspice data file held no numbers.")
    return rows


def _log_tail(text: str, lines: int = 12) -> str:
    tail = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(tail[-lines:])


def run_analysis(analysis: str, params: dict,
                 timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    """Run one analysis in its own directory and return parsed results."""
    if analysis not in ANALYSES:
        raise SpiceError("bad_analysis", f"Unknown analysis '{analysis}'.")

    exe = find_ngspice()
    if exe is None:
        raise SpiceError(
            "engine_missing",
            "ngspice was not found. Install it, or set NGSPICE_BIN to the "
            "console executable.",
        )

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{stamp}-{analysis}-{uuid.uuid4().hex[:6]}"
    run_dir.mkdir(parents=True)

    netlist = build_netlist(params, analysis)
    cir_path = run_dir / "circuit.cir"
    cir_path.write_text(netlist, encoding="ascii")

    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(exe), "-b", "-o", "run.log", cir_path.name],
            cwd=str(run_dir), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SpiceError(
            "timeout",
            f"ngspice did not finish within {timeout:.0f} s.",
            f"run directory: {run_dir}",
        ) from exc
    except OSError as exc:
        raise SpiceError("engine_missing", "Could not start ngspice.",
                         str(exc)) from exc
    duration_ms = (time.perf_counter() - started) * 1000.0

    log_path = run_dir / "run.log"
    log_text = ""
    if log_path.is_file():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")

    if proc.returncode != 0:
        raise SpiceError(
            "run_failed",
            f"ngspice exited with code {proc.returncode}.",
            _log_tail(log_text or proc.stderr or ""),
        )
    if re.search(r"^\s*(Error|Fatal error)", log_text, re.MULTILINE):
        raise SpiceError("run_failed", "ngspice reported an error.",
                         _log_tail(log_text))

    result = {
        "analysis": analysis,
        "analysis_name": ANALYSIS_NAMES[analysis],
        "engine": engine_info(),
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "netlist": netlist,
        "log_tail": _log_tail(log_text, 20),
        "duration_ms": duration_ms,
        "command": f"{exe.name} -b -o run.log {cir_path.name}",
    }

    if analysis == "dc":
        result["dc"] = _parse_op(parse_wrdata(run_dir / "op.txt"))
    elif analysis == "ac":
        result["ac"] = _parse_ac(parse_wrdata(run_dir / "ac.txt"))
    else:
        result["tran"] = _parse_tran(
            parse_wrdata(run_dir / "tran.txt"), params["freq"])
    return result


def _parse_op(rows: list) -> dict:
    if not rows or len(rows[0]) < 7:
        raise SpiceError("empty_output", "Operating point data was incomplete.")
    row = rows[0]
    vb = row[0][1]
    vc = row[1][1]
    ve = row[2][1]
    ic = row[4][1]
    ib = row[5][1]
    ie = abs(row[6][1])
    vce = vc - ve
    if ic <= 1e-9:
        region = "cutoff"
    elif vce <= 0.2:
        region = "saturation"
    else:
        region = "active"
    return {
        "vb_v": vb, "ve_v": ve, "vc_v": vc, "vce_v": vce,
        "ic_ma": ic * 1e3, "ib_ua": ib * 1e6, "ie_ma": ie * 1e3,
        "region": region,
    }


def _parse_ac(rows: list) -> dict:
    if not rows or len(rows[0]) < 4:
        raise SpiceError("empty_output", "AC data was incomplete.")
    # Each row holds four (scale, value) pairs: out dB, out phase,
    # src dB, src phase. Gain and phase are referenced to the source.
    freq = [row[0][0] for row in rows]
    gain_db = [row[0][1] for row in rows]
    # ngspice's vp() returns radians, and wraps at +/-pi. Convert the
    # out-minus-in difference to degrees and unwrap for a continuous Bode curve.
    phase_deg = _unwrap_degrees(
        [math.degrees(row[1][1] - row[3][1]) for row in rows])
    src_db = [row[2][1] for row in rows]

    gain_at_1k = _interp_log(freq, gain_db, 1000.0)
    low, high = _cutoffs(freq, gain_db, gain_at_1k)
    return {
        "freq_hz": freq,
        "gain_db": gain_db,
        "phase_deg": phase_deg,
        "src_db": src_db,
        "gain_db_at_1k": gain_at_1k,
        "gain_at_1k": 10 ** (gain_at_1k / 20.0) if gain_at_1k is not None else None,
        "f_low_hz": low,
        "f_high_hz": high,
        "sweep_start_hz": AC_START_HZ,
        "sweep_stop_hz": AC_STOP_HZ,
        "points_per_decade": AC_POINTS_PER_DECADE,
    }


def _unwrap_degrees(values: list) -> list:
    """Remove the +/-180 degree jumps from a wrapped phase curve."""
    if not values:
        return []
    out = [values[0]]
    for value in values[1:]:
        previous = out[-1]
        while value - previous > 180.0:
            value -= 360.0
        while value - previous < -180.0:
            value += 360.0
        out.append(value)
    return out


def _interp_log(xs: list, ys: list, target: float) -> Optional[float]:
    if not xs:
        return None
    if target <= xs[0]:
        return ys[0]
    if target >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if xs[i] >= target:
            x0, x1 = xs[i - 1], xs[i]
            y0, y1 = ys[i - 1], ys[i]
            if x1 == x0:
                return y0
            ratio = (math.log10(target) - math.log10(x0)) / (
                math.log10(x1) - math.log10(x0))
            return y0 + ratio * (y1 - y0)
    return ys[-1]


def _cutoffs(freq: list, gain_db: list, reference: Optional[float]) -> tuple:
    """-3 dB corners relative to the 1 kHz gain, or None inside this sweep."""
    if reference is None:
        return None, None
    threshold = reference - 3.0
    low = None
    high = None
    for f, g in zip(freq, gain_db):
        if f <= 1000.0 and g <= threshold:
            low = f
    for f, g in zip(freq, gain_db):
        if f >= 1000.0 and g <= threshold:
            high = f
            break
    return low, high


def _parse_tran(rows: list, freq: float) -> dict:
    if not rows or len(rows[0]) < 3:
        raise SpiceError("empty_output", "Transient data was incomplete.")
    # Each row holds three (scale, value) pairs: time, v(src), v(out).
    time_s = [row[0][0] for row in rows]
    vin = [row[1][1] for row in rows]
    vout = [row[2][1] for row in rows]
    if len(time_s) < 10:
        raise SpiceError("empty_output", "Transient data was incomplete.")

    period = 1.0 / freq
    window_start = max(time_s[-1] - 3.0 * period, time_s[0])
    idx = [i for i, t in enumerate(time_s) if t >= window_start]
    if len(idx) < 5:
        idx = list(range(max(0, len(time_s) - 50), len(time_s)))
    t_ms = [time_s[i] * 1e3 for i in idx]
    vin_w = [vin[i] for i in idx]
    vout_w = [vout[i] for i in idx]

    vin_peak = max(abs(v) for v in vin_w)
    vout_peak = max(abs(v) for v in vout_w)
    mean_in = sum(vin_w) / len(vin_w)
    mean_out = sum(vout_w) / len(vout_w)
    covariance = sum((a - mean_in) * (b - mean_out)
                     for a, b in zip(vin_w, vout_w))
    return {
        "time_ms": t_ms,
        "vin_mv": [v * 1e3 for v in vin_w],
        "vout_mv": [v * 1e3 for v in vout_w],
        "vin_peak_mv": vin_peak * 1e3,
        "vout_peak_mv": vout_peak * 1e3,
        "gain": (vout_peak / vin_peak) if vin_peak > 0 else None,
        "inverted": covariance < 0,
        "window_periods": 3,
        "stop_s": time_s[-1],
    }
