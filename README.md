# BJT Common-Emitter DC Bias Calculator

A one-page Flask app for **ENG29 2121**: enter the seven bias values of an NPN
common-emitter stage with voltage-divider bias and get the DC operating point
with units, input validation, an operating-region warning, and an independent
second calculation to compare against.

No AC analysis, no transient, no Bode plots, no schematic editor — DC bias
only.

## Model

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

Open <http://127.0.0.1:5000/>.

The Flask development server binds to localhost only. Do not expose it to a
network, and never commit `.venv/`, `.env`, API keys, or credentials.

## Test

```bash
python -m unittest discover -s tests -v
```

14 tests: 6 engineering checks (exact solution, cutoff, saturation,
approximation convergence, comparison rule, refusal to validate the
approximation outside the active region), 5 validation checks, and 3 HTTP
checks through the Flask test client.

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

## Acceptance mapping

| Item | Where |
|---|---|
| A1 · GET / shows the input form, HTTP 200 | `app.py` `index()`; `tests/test_routes.py::test_get_index_shows_form` |
| A2 · POST /calculate renders computed values | `app.py` `calculate()` → `bias.calculator`; `test_post_computes_and_renders` |
| A3 · Values agree with an independent calculation | `bias/calculator.py` `solve_approximate` + `compare`; `test_comparison_reports_rule_and_delta` |
| A4 · Invalid input shows errors, page survives | `bias/validation.py`; `tests/test_validation.py`, `test_post_rejects_bad_input_without_crashing` |
| A5 · Cutoff / saturation warning, approximation not claimed valid | `bias/calculator.py` region logic; `test_approximation_never_valid_outside_active_region` |
| A6 · ≥3 engineering tests + ≥1 HTTP test | `tests/` (14 tests) |
| A7 · Clone, install, run, test from README | this file |

## Layout

```
app.py                  Flask routes and unit formatting
bias/calculator.py      DC model (no Flask imports)
bias/validation.py      form parsing and range rules
templates/index.html    form, results, comparison, warnings
static/style.css        plain readable styling
tests/                  unittest suite
docs/superpowers/       design and implementation plan
```
