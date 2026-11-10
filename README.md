# BJT Common-Emitter DC Bias Calculator

A one-page Flask app for **ENG29 2121**: enter the seven bias values of an NPN
common-emitter stage with voltage-divider bias and get the DC operating point
with units, input validation, an operating-region warning, and an independent
second calculation to compare against.

No AC analysis, no transient, no Bode plots, no schematic editor โ€” DC bias
only.

## Model

```
VBB = VCC ยท R2 / (R1 + R2)          Thรฉvenin base voltage
RB  = R1 โฅ R2                       Thรฉvenin base resistance

IB  = (VBB โ’ VBE) / (RB + (1 + ฮฒ)ยทRE)      exact (base loop, KVL)
IC  = ฮฒ ยท IB
IE  = (1 + ฮฒ) ยท IB
VE  = IE ยท RE
VB  = VE + VBE
VC  = VCC โ’ IC ยท RC
VCE = VC โ’ VE
```

The independent check drops ฮฒ entirely (stiff divider, IB โ 0):

```
VB = VBB ,  VE = VB โ’ VBE ,  IE = VE / RE ,  IC โ IE ,  VCE = VCC โ’ ICยท(RC + RE)
```

The two results are compared with a percentage difference and the stiffness
rule `ฮฒยทRE โฅ 10ยทR2`. When the transistor is cut off or saturated the
approximation is never reported as valid.

Region rules (`VCE_SAT = 0.2 V`, set in `bias/calculator.py`):

| Region | Condition |
|---|---|
| cutoff | `VBB โค VBE` โ’ IB = IC = IE = 0, VCE = VCC |
| saturation | `VCE < 0.2 V` โ’ model values invalid, `IC_sat = (VCC โ’ 0.2)/(RC + RE)` |
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

Resistors are entered in **kOhm** on the form; the app converts them to ohms before the engineering layer runs.

Open <http://127.0.0.1:5000/>.

The Flask development server binds to localhost only. Do not expose it to a
network, and never commit `.venv/`, `.env`, API keys, or credentials.

## Test

```bash
python -m unittest discover -s tests -v
```

17 tests: 8 engineering checks (exact solution, cutoff, saturation,
approximation convergence, comparison rule, refusal to validate the
approximation outside the active region), 5 validation checks, and 3 HTTP
checks through the Flask test client.

## Worked example

`VCC = 12 V, R1 = 47 kฮฉ, R2 = 10 kฮฉ, RC = 2.2 kฮฉ, RE = 1 kฮฉ, ฮฒ = 150, VBE = 0.7 V`

| Quantity | Exact | Approximate |
|---|---|---|
| VB | 2.032 V | 2.105 V |
| VE | 1.332 V | 1.405 V |
| VC | 9.088 V | 8.908 V |
| VCE | 7.755 V | 7.503 V |
| IB | 8.825 ยตA | โ€” |
| IC | 1.324 mA | 1.405 mA |
| IE | 1.333 mA | 1.405 mA |

Region: **active**. ฮ”IC = 6.16 %, ฮ”VCE = 3.25 %,
`ฮฒยทRE / R2 = 15` โ’ approximation valid.

## Acceptance mapping

| Item | Where |
|---|---|
| A1 ยท GET / shows the input form, HTTP 200 | `app.py` `index()`; `tests/test_routes.py::test_get_index_shows_form` |
| A2 ยท POST /calculate renders computed values | `app.py` `calculate()` โ’ `bias.calculator`; `test_post_computes_and_renders` |
| A3 ยท Values agree with an independent calculation | `bias/calculator.py` `solve_approximate` + `compare`; `test_comparison_reports_rule_and_delta` |
| A4 ยท Invalid input shows errors, page survives | `bias/validation.py`; `tests/test_validation.py`, `test_post_rejects_bad_input_without_crashing` |
| A5 ยท Cutoff / saturation warning, approximation not claimed valid | `bias/calculator.py` region logic; `test_approximation_never_valid_outside_active_region` |
| A6 ยท โฅ3 engineering tests + โฅ1 HTTP test | `tests/` (17 tests) |
| A7 ยท Clone, install, run, test from README | this file |

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
