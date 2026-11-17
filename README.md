# Git-Lab

ใช้สำหรับ lab compro

---

# Lab 02/03: BJT Common-Emitter DC Bias Calculator

A Flask web app for **ENG29 2121**: enter the bias values of an NPN
common-emitter stage and get the DC operating point with units, input
validation, an operating-region warning, and (for the divider topology) an
independent second calculation to compare against.

Three single-supply topologies share one DC model and one result shape:
**Fixed Bias**, **Emitter Bias** and **Voltage Divider Bias**.

No AC analysis, no transient, no Bode plots, no schematic editor — DC bias
only.

## Lab 03 submission

| Item | Value |
|---|---|
| Repository | <https://github.com/thanpitcha29/Git-Lab> |
| Branch | `main` |
| Commit | `90274dc` |
| A1–A5 acceptance table, evidence, independent reference, AI/student split | [`docs/validation.md`](docs/validation.md) |
| Screenshot evidence (case A2) | [`docs/evidence-a2-fixed-bias.jpg`](docs/evidence-a2-fixed-bias.jpg) |

Reproduce it with the **Setup**, **Run** and **Test** sections below; the app
opens at <http://127.0.0.1:5000/>.

What AI wrote: the three solver functions and the shared finishing step in
`bias/calculator.py`, the mode-aware validation in `bias/validation.py`, the
`if / elif` dispatch in `app.py`, and the template/CSS. What the student
checked: the equations against the lab sheet, at least one hand calculation
per mode, the Divider result staying at 1.23 mA / 8.05 V, and the A1–A5 runs
repeated in the browser.

## Bias modes

Common inputs for all three: `VCC`, `RC`, `β`, `VBE`.

| Mode | Extra inputs | Base network | Emitter network |
|---|---|---|---|
| Fixed | — | `RB` from VCC to base | none (emitter grounded) |
| Emitter | `RE` | `RB` from VCC to base | `RE` from emitter to ground |
| Divider | `R1`, `R2`, `RE` | `R1` from VCC to base, `R2` from base to ground | `RE` from emitter to ground |

```
Fixed    IB = (VCC - VBE) / RB                       VE = 0
Emitter  IB = (VCC - VBE) / (RB + (β + 1)·RE)        VE = IE·RE
Divider  IB = (VTH - VBE) / (RTH + (β + 1)·RE)       VE = IE·RE
         VTH = VCC·R2/(R1+R2)   RTH = R1·R2/(R1+R2)
then     IC = β·IB ,  IE = (β + 1)·IB ,  VB = VE + VBE
         VC = VCC - IC·RC ,  VCE = VC - VE
```

The form takes resistors in **kOhm** and converts them to ohm once, at the
point where the request is parsed. Every mode returns the same keys and units:
`vb_v, ve_v, vc_v, vce_v, ic_ma, ib_ma, ib_ua, ie_ma, region, warning`.

## Model (Voltage Divider)

```
VBB = VCC · R2 / (R1 + R2)          Thévenin base voltage
RB  = R1 ∥ R2                       Thévenin base resistance

IB  = (VBB − VBE) / (RB + (1 + β)·RE)      exact (base loop, KVL)
IC  = β · IB
IE  = (1 + β) · IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

The independent check drops β entirely (stiff divider, IB ≈ 0):

```
VB = VBB ,  VE = VB − VBE ,  IE = VE / RE ,  IC ≈ IE ,  VCE = VCC − IC·(RC + RE)
```

The two results are compared with a percentage difference and the stiffness
rule `β·RE ≥ 10·R2`. When the transistor is cut off or saturated the
approximation is never reported as valid.

Region rules (`VCE_SAT = 0.2 V`, set in `bias/calculator.py`):

| Region | Condition |
|---|---|
| cutoff | `VBB ≤ VBE` → IB = IC = IE = 0, VCE = VCC |
| saturation | `VCE < 0.2 V` → model values invalid, `IC_sat = (VCC − 0.2)/(RC + RE)` |
| active | otherwise |

## Setup

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python -m flask --app app run --debug
```

Resistors are entered in **kOhm** on the form; the app converts them to ohms
before the engineering layer runs.

Open <http://127.0.0.1:5000/>.

The Flask development server binds to localhost only. Do not expose it to a
network, and never commit `.venv/`, `.env`, API keys, or credentials.

## Test

```bash
python -m unittest discover -s tests -v
```

18 tests: 7 engineering checks, 5 validation checks, and 6 HTTP checks through
the Flask test client — including the three-mode dispatch, the unknown-mode
rejection, kΩ → Ω scaling, and the input-error path.

## Worked example

`VCC = 12 V, R1 = 47 kΩ, R2 = 10 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 150, VBE = 0.7 V`

| Quantity | Exact | Approximate |
|---|---|---|
| VB | 2.032 V | 2.105 V |
| VE | 1.332 V | 1.405 V |
| VC | 9.088 V | 8.908 V |
| VCE | 7.755 V | 7.503 V |
| IB | 8.825 µA | — |
| IC | 1.324 mA | 1.405 mA |
| IE | 1.333 mA | 1.405 mA |

Region: **active**. ΔIC = 6.16 %, ΔVCE = 3.25 %,
`β·RE / R2 = 15` → approximation valid.

## Acceptance mapping (Lab 03)

| Item | Where |
|---|---|
| A1 · Divider still correct, unchanged from Lab 02 | `solve_divider()` wraps `solve_exact()`; `docs/validation.md` A1 |
| A2 · Fixed bias (no RE, VE = 0) | `solve_fixed()`; `app.py` `elif mode == "fixed"` |
| A3 · Emitter bias uses RE | `solve_emitter()`; RE listed in `MODES["emitter"]` and `FIELDS["emitter"]` |
| A4 · Doubling RE lowers IC | observed 1.03 → 0.94 mA in `docs/validation.md` A4 |
| A5 · Bad input rejected, page survives | `bias/validation.py` (`RB > 0`); `test_post_rejects_bad_input_without_crashing` |
| Same keys/units for all modes | `_point()` returns `vb_v … ie_ma` + `region` + `warning` |
| Unknown mode never falls back to Divider | `validate_mode()` + `unknown_mode_error()`; `test_unknown_mode_is_rejected` |
| ≥3 engineering tests + ≥1 HTTP test | `tests/` (18 tests) |
| Clone, install, run, test from README | this file |

## Layout

```
app.py                  Flask routes and unit formatting
bias/calculator.py      DC model (no Flask imports)
bias/validation.py      form parsing and range rules
templates/index.html    form, results, comparison, warnings
static/style.css        lab-style layout and schematic
tests/                  unittest suite
docs/superpowers/       design and implementation plan
REFLECTION.md           student reflection
```

## Assumptions

- VBE is constant and supplied by the user (no temperature dependence).
- β is constant and equal to IC/IB (no Early effect, no leakage).
- The transistor is ideal outside the active region: it is off in cutoff
  (`VBB <= VBE`) and its collector-emitter voltage cannot fall below
  `VCE,sat = 0.2 V` in saturation.
- Resistors are ideal and independent of temperature; the DC model has no
  capacitances, so there is no frequency behaviour.
