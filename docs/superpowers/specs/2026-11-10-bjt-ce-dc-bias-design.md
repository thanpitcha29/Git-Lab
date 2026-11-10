# BJT Common-Emitter DC Bias Calculator — Design

Course: ENG29 2121 · Lab deliverable
Date: 2026-11-10
Status: Awaiting student approval

## 1. Intent and why

A student needs a small, demonstrable Flask web app that computes the DC
operating point of an NPN common-emitter amplifier with voltage-divider bias,
shows the result with units, refuses bad input, warns when the transistor is
outside the active region, and cross-checks the answer against a second,
independent engineering calculation. It must run on localhost, pass automated
tests, clone cleanly from GitHub, and be finished inside one lab session.

The point is not a simulator. It is evidence that the student can separate
engineering logic from web plumbing, validate input, and justify a result.

## 2. Goals

- G1 — Real server-side computation in Python; no hard-coded results in HTML.
- G2 — DC operating point with units: IB, IC, IE, VB, VE, VC, VCE.
- G3 — An independent second calculation, shown next to the first, with a
  percentage difference and a stated validity rule.
- G4 — Clear validation errors; the page never returns a 500 for user input.
- G5 — Operating-region detection (active / saturation / cutoff) with warnings.
- G6 — Automated tests: engineering math + Flask HTTP.
- G7 — Reproducible from a fresh clone via README.

## 3. Non-goals

AC analysis, small-signal/h-parameters, frequency response, Bode plots,
transient simulation, function generator, oscilloscope view, circuit schematic
editor, component database, MOSFET/JFET support, PNP, user accounts, database,
JavaScript framework, decorative UI, deployment to a public host.

## 4. Anti-goals (this would count as failure even if it runs)

- Numbers produced in the template or in JavaScript instead of Python.
- Tests that assert the function under test against itself.
- A second method that is a copy-paste of the first.
- Reporting "approximation is valid" while the device is saturated or cut off.
- Claiming tests pass without running them.

## 5. Constraints

- Python 3.12 (available), Flask, standard library `unittest`.
- Windows dev machine; must also work on Linux/macOS (path-separator safe).
- Single page, no client-side framework, no build step.
- `RE > 0` is mandatory: the approximate method divides by RE, and the
  base-loop model is undefined at zero emitter resistance.
- Flask debug server only on 127.0.0.1; never committed `.venv/`, `.env`,
  credentials.

## 6. Approaches considered

| # | Approach | Verdict |
|---|----------|---------|
| A | Exact base-loop solution (KVL with IB) + textbook approximate method (IB ≈ 0) as the independent check | **Chosen.** Both are closed-form, hand-checkable, and the approximate method is exactly what the student computes by hand in the lab. Satisfies A3 and A5 with ~40 lines of logic. |
| B | Exact solution + Newton/nodal numeric solver as the independent check | Rejected. Numerically it converges to the same model; adds dependency and failure modes without adding engineering insight at this level. |
| C | Exact solution + hard-coded reference values from the lab sheet | Rejected. Not independent for arbitrary input, and it is a table, not a calculation. |

## 7. Engineering model (single model, two routes)

NPN, voltage-divider bias, constant-VBE / ideal-current-gain model.
Inputs: `VCC, R1, R2, RC, RE, beta, VBE`.

Thévenin equivalent of the base divider:

```
VBB = VCC * R2 / (R1 + R2)
RB  = R1 * R2 / (R1 + R2)
```

### Route 1 — Exact (default result)

Base-emitter loop, KVL:

```
VBB = IB*RB + VBE + IE*RE ,  IE = (1 + beta) * IB
IB  = (VBB - VBE) / (RB + (1 + beta)*RE)
IC  = beta * IB
IE  = (1 + beta) * IB
VE  = IE * RE
VB  = VE + VBE
VC  = VCC - IC * RC
VCE = VC - VE
```

### Route 2 — Approximate, beta-independent (independent check)

Assumes the divider is stiff and IB is negligible:

```
VB = VBB
VE = VB - VBE
IE = VE / RE
IC ≈ IE
VC = VCC - IC*RC
VCE = VC - VE
```

Note this route never uses `beta`, so it is a genuinely different computation
path over the same physical model.

### Comparison

```
delta_pct(IC)  = |IC_approx - IC_exact| / |IC_exact| * 100
delta_pct(VCE) = |VCE_approx - VCE_exact| / |VCE_exact| * 100
valid_rule     = (beta * RE) >= (10 * R2)     # Boylestad / Sedra-Smith rule
```

`delta_pct` is reported for IC and VCE, plus the ratio `beta*RE / R2` so the
student can see how far from "stiff" the design is.

### Operating region

Evaluated on the exact result:

| Region | Condition | Reported values |
|--------|-----------|-----------------|
| cutoff | `VBB <= VBE` (IB would be ≤ 0) | IB=IC=IE=0, VE=0, VB=VBB, VC=VCC, VCE=VCC |
| saturation | `VCE < VCE_SAT` (constant `VCE_SAT = 0.2 V`) | model values reported as *invalid*, plus `IC_sat = (VCC - VCE_SAT) / (RC + RE)` as the physical ceiling |
| active | otherwise | model values are valid |

When the region is not active, `approximation_valid` is forced to `False` and
the page says the small-signal bias point is not usable (A5).

The approximate route applies the same region test so the comparison is
like-for-like.

## 8. Validation (`bias/validation.py`)

Each field is parsed as a float and checked; all errors are collected and shown
together, never raised as an exception.

| Field | Rule | Message (English) |
|-------|------|-------------------|
| all | must parse as a number | "<field> must be a number" |
| all | finite (no `inf`/`nan`) | "<field> must be a finite number" |
| VCC | > 0 | "VCC must be greater than 0 V" |
| R1, R2 | > 0 | "R1 must be greater than 0 Ω" |
| RC | ≥ 0 | "RC must be 0 Ω or greater" |
| RE | > 0 | "RE must be greater than 0 Ω (the model needs an emitter resistor)" |
| beta | > 0 | "beta must be greater than 0" |
| VBE | ≥ 0 | "VBE must be 0 V or greater" |

Invalid input → form re-rendered with HTTP 200, the submitted values kept, and
an error list; nothing is computed.

## 9. Web surface

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/` | empty form, defaults VCC=12, R1=47000, R2=10000, RC=2200, RE=1000, beta=150, VBE=0.7 |
| POST | `/calculate` | validate → compute → render results on the same page; errors re-render the form |

No API endpoints, no JSON, no auth.

## 10. File layout (one responsibility per file)

```
app.py                    Flask app factory + routes only
bias/__init__.py
bias/validation.py        parse + validate raw form strings -> dataclass or errors
bias/calculator.py        exact(), approximate(), compare(), region logic (no Flask)
templates/base.html       document shell
templates/index.html      form + results + warnings + comparison table
static/style.css          plain readable styling
tests/test_calculator.py  engineering math (reference vectors)
tests/test_validation.py  validation rules
tests/test_routes.py      Flask test client HTTP behavior
requirements.txt          flask, pytest optional (unittest is stdlib)
README.md                 setup, run, test, acceptance mapping
docs/superpowers/specs/   this document
.gitignore                .venv/, __pycache__/, .env
```

## 11. Test plan

Engineering (reference values computed by hand, hard-coded, not derived from the
implementation):

| Case | Inputs (VCC, R1, R2, RC, RE, beta, VBE) | Expected |
|------|------------------------------------------|----------|
| E1 active | 12, 47k, 10k, 2.2k, 1k, 150, 0.7 | IC = 1.32368 mA, VCE = 7.75541 V, VB = 2.0325 V, VE = 1.3325 V, VC = 9.08791 V |
| E2 cutoff | 12, 100k, 5k, 2.2k, 1k, 150, 0.7 | region cutoff, IC = 0, VCE = 12 V |
| E3 saturation | 12, 47k, 10k, 10k, 1k, 150, 0.7 | region saturation, IC_sat = (12−0.2)/(10k+1k) = 1.0727 mA |
| E4 stiff divider | 12, 47k, 10k, 2.2k, 1k, 300, 0.7 | exact vs approximate IC within 5 % |
| E5 comparison flag | same as E1 | rule βRE ≥ 10R2 true, delta_IC ≈ 6.16 % |

Validation: non-numeric, zero/negative R, β ≤ 0, RE = 0, VCC ≤ 0.

HTTP (Flask test client): GET `/` → 200 and form present; POST valid → 200 and
computed value in body; POST garbage → 200 and error text, no traceback.

## 12. Acceptance mapping

| Item | Covered by |
|------|-----------|
| A1 GET / | route + `test_routes` |
| A2 POST /calculate | route calls `bias.calculator`, no hard-coded HTML |
| A3 Engineering reference | `test_calculator` reference vectors + comparison table in UI |
| A4 Validation | `bias.validation` + `test_validation` + `test_routes` |
| A5 Outside active region | region logic, approximation validity forced False + warning block |
| A6 Unit + HTTP tests | `tests/` (3+ math, 1+ HTTP) |
| A7 GitHub reproducibility | `README.md` + `.gitignore` + `requirements.txt` |

## 13. Decisions taken by the assistant (student may override)

1. Approximate β-independent method is the "independent calculation"
   (A3 says "under the same model", A5 mentions approximation validity).
2. `VCE_SAT = 0.2 V` as a named constant in `calculator.py`.
3. UI copy in English to match the lab vocabulary on the acceptance sheet.
4. Invalid input returns HTTP 200 with an error block (page never "breaks").
5. Currents displayed in mA (IB additionally in µA), voltages in V, 3 decimals.

## 14. Left to the builder

Exact HTML structure and CSS styling; wording of region messages; whether the
comparison table is a `<table>` or a definition list. None of these change the
engineering result.
