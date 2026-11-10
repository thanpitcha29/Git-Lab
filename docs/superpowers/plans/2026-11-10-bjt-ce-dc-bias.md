# BJT Common-Emitter DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single-page Flask app that solves the DC operating point of a voltage-divider-biased NPN common-emitter stage, validates input, warns about the operating region, and cross-checks the answer against the β-independent approximate method.

**Architecture:** Pure engineering math in `bias/calculator.py` (no Flask imports), parsing/validation in `bias/validation.py`, thin routes in `app.py`, one Jinja template and one stylesheet. Standard-library `unittest` only — no pytest dependency.

**Tech Stack:** Python 3.12, Flask 3.x, Jinja2, `unittest`, Git.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-dc-bias-design.md`

## Global Constraints

- Python 3.12; Flask only runtime dependency (`requirements.txt`: `flask>=3.0`).
- Tests run with `python -m unittest discover -s tests -v` and must pass from a fresh clone.
- Only `VCE_SAT = 0.2` V is threshold-tunable; it lives in `bias/calculator.py`.
- Display: voltages in V, IC/IE in mA, IB in mA and µA, 3 decimals.
- Invalid user input returns HTTP 200 with an error block; never a 500 and never a traceback in the body.
- `bias/calculator.py` and `bias/validation.py` must not import Flask or Jinja.
- `.venv/`, `__pycache__/`, `.env` never committed.
- UI copy in English.

## Review Focus

- Missing or empty form field → field-level error message, no `KeyError`.
- Non-numeric text (`"12k"`, `"1,000"`, `""`) → parse error message, no traceback.
- `RC = 0` is legal (rule is `RC ≥ 0`) → `VC = VCC`, no division by zero anywhere.
- Saturation with negative computed `VCE` → percentages use absolute value, no negative percentage, no crash.
- `beta < 1` (e.g. 0.5) is not forbidden by the rules → finite result, no crash.

---

### Task 1: Repo scaffold and exact DC solver

**Files:**
- Create: `.gitignore`, `requirements.txt`, `bias/__init__.py`, `bias/calculator.py`, `tests/test_calculator.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `bias.calculator.VCE_SAT: float`; `bias.calculator.OperatingPoint` frozen dataclass with fields `VBB, RB, IB, IC, IE, VE, VB, VC, VCE: float` and `region: str`; `bias.calculator.solve_exact(VCC: float, R1: float, R2: float, RC: float, RE: float, beta: float, VBE: float) -> OperatingPoint`. Task 2 fills in the `cutoff`/`saturation` branches; Task 3 consumes this signature unchanged.

- [ ] **Step 1: Create the repository and environment**

```bash
git init -b main
python -m venv .venv
.venv/Scripts/python -m pip install "flask>=3.0"
```

Write `.gitignore` (`.venv/`, `__pycache__/`, `*.pyc`, `.env`, `.pytest_cache/`), `requirements.txt` (`flask>=3.0`), and an empty `bias/__init__.py`.

- [ ] **Step 2: Write the failing test for the active-region case**

`tests/test_calculator.py`:

```python
import unittest
from bias.calculator import solve_exact

DEFAULTS = dict(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=2_200.0,
               RE=1_000.0, beta=150.0, VBE=0.7)


class ExactSolverTest(unittest.TestCase):
    def test_active_case(self):
        op = solve_exact(**DEFAULTS)
        self.assertEqual(op.region, "active")
        self.assertAlmostEqual(op.IB, 8.824501487e-06, places=9)
        self.assertAlmostEqual(op.IC, 1.323675223e-03, places=9)
        self.assertAlmostEqual(op.IE, 1.332499725e-03, places=9)
        self.assertAlmostEqual(op.VE, 1.3324997246, places=6)
        self.assertAlmostEqual(op.VB, 2.0324997246, places=6)
        self.assertAlmostEqual(op.VC, 9.0879145092, places=6)
        self.assertAlmostEqual(op.VCE, 7.7554147846, places=6)
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `.venv/Scripts/python -m unittest discover -s tests -k test_active_case -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bias.calculator'`.

- [ ] **Step 4: Implement `OperatingPoint` and `solve_exact`**

In `bias/calculator.py`: `VCE_SAT = 0.2`. `solve_exact` computes `VBB = VCC*R2/(R1+R2)`, `RB = R1*R2/(R1+R2)`, `IB = (VBB-VBE)/(RB+(1+beta)*RE)`, then `IC = beta*IB`, `IE = (1+beta)*IB`, `VE = IE*RE`, `VB = VE+VBE`, `VC = VCC-IC*RC`, `VCE = VC-VE`, and sets `region="active"` unconditionally for now.

- [ ] **Step 5: Run the test to confirm it passes, then commit**

Run: `.venv/Scripts/python -m unittest discover -s tests -v`
Expected: 1 test, OK.

```bash
git add .gitignore requirements.txt bias/ tests/
git commit -m "feat: exact DC operating point solver"
```

---

### Task 2: Operating-region detection

**Files:**
- Modify: `bias/calculator.py`
- Test: `tests/test_calculator.py`

**Interfaces:**
- Consumes: `solve_exact`, `OperatingPoint`, `VCE_SAT` from Task 1.
- Produces: same signature `solve_exact(...)`, now returning `region in {"active","cutoff","saturation"}` and `IC_sat: float | None` added to `OperatingPoint`. Task 3 and Task 5 rely on `region` and `IC_sat`.

- [ ] **Step 1: Write the failing cutoff and saturation tests**

```python
    def test_cutoff_when_divider_below_vbe(self):
        op = solve_exact(VCC=12.0, R1=100_000.0, R2=5_000.0, RC=2_200.0,
                         RE=1_000.0, beta=150.0, VBE=0.7)
        self.assertEqual(op.region, "cutoff")
        self.assertEqual((op.IB, op.IC, op.IE, op.VE), (0.0, 0.0, 0.0, 0.0))
        self.assertAlmostEqual(op.VB, 0.5714286, places=6)
        self.assertAlmostEqual(op.VC, 12.0, places=9)
        self.assertAlmostEqual(op.VCE, 12.0, places=9)

    def test_saturation_when_vce_below_threshold(self):
        op = solve_exact(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=10_000.0,
                         RE=1_000.0, beta=150.0, VBE=0.7)
        self.assertEqual(op.region, "saturation")
        self.assertLess(op.VCE, 0.2)
        self.assertAlmostEqual(op.IC_sat, 11.8 / 11_000.0, places=9)  # (12-0.2)/(10k+1k)
```

- [ ] **Step 2: Run to confirm both fail**

Run: `.venv/Scripts/python -m unittest discover -s tests -k cutoff -v` then `-k saturation`
Expected: FAIL — region is `"active"`, `IC_sat` attribute missing.

- [ ] **Step 3: Add the region branches**

If `VBB <= VBE`: return `OperatingPoint` with `IB=IC=IE=VE=0.0`, `VB=VBB`, `VC=VCC`, `VCE=VCC`, `region="cutoff"`, `IC_sat=None`. Else compute as in Task 1, then set `region = "saturation"` and `IC_sat = (VCC - VCE_SAT)/(RC + RE)` when `VCE < VCE_SAT`, otherwise `"active"` and `IC_sat=None`.

- [ ] **Step 4: Run the full suite, then commit**

Run: `.venv/Scripts/python -m unittest discover -s tests -v`
Expected: 3 tests, OK.

```bash
git add bias/calculator.py tests/test_calculator.py
git commit -m "feat: detect cutoff and saturation regions"
```

---

### Task 3: Approximate method and comparison

**Files:**
- Modify: `bias/calculator.py`
- Test: `tests/test_calculator.py`

**Interfaces:**
- Consumes: `solve_exact`, `OperatingPoint` (Tasks 1–2).
- Produces: `bias.calculator.Comparison` frozen dataclass with `approx: OperatingPoint`, `delta_ic_pct: float | None`, `delta_vce_pct: float | None`, `beta_re_over_r2: float`, `rule_satisfied: bool`, `approximation_valid: bool`; `solve_approximate(VCC, R1, R2, RC, RE, beta, VBE) -> OperatingPoint`; `compare(exact: OperatingPoint, approx: OperatingPoint, beta: float, RE: float, R2: float) -> Comparison`. Task 5 renders `delta_ic_pct`, `delta_vce_pct`, `beta_re_over_r2`, `rule_satisfied`, `approximation_valid`.

- [ ] **Step 1: Write the failing approximate/comparison tests**

```python
    def test_approximate_matches_exact_on_stiff_divider(self):
        kwargs = dict(DEFAULTS, beta=300.0)
        exact = solve_exact(**kwargs)
        approx = solve_approximate(**kwargs)
        self.assertLess(abs(approx.IC - exact.IC) / abs(exact.IC) * 100, 5.0)

    def test_comparison_reports_rule_and_delta(self):
        exact = solve_exact(**DEFAULTS)
        approx = solve_approximate(**DEFAULTS)
        cmp = compare(exact, approx, beta=150.0, RE=1_000.0, R2=10_000.0)
        self.assertTrue(cmp.rule_satisfied)          # 150k >= 10*10k
        self.assertAlmostEqual(cmp.beta_re_over_r2, 15.0)
        self.assertAlmostEqual(cmp.delta_ic_pct, 6.16374, places=3)
        self.assertTrue(cmp.approximation_valid)

    def test_approximation_never_valid_outside_active_region(self):
        exact = solve_exact(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=10_000.0,
                            RE=1_000.0, beta=150.0, VBE=0.7)
        approx = solve_approximate(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=10_000.0,
                                   RE=1_000.0, beta=150.0, VBE=0.7)
        cmp = compare(exact, approx, beta=150.0, RE=1_000.0, R2=10_000.0)
        self.assertFalse(cmp.approximation_valid)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `.venv/Scripts/python -m unittest discover -s tests -k comparison -v`
Expected: FAIL — `solve_approximate` / `compare` not defined.

- [ ] **Step 3: Implement both**

`solve_approximate` mirrors Task 2's region handling but computes `VB=VBB`, `VE=VB-VBE`, `IE=VE/RE`, `IC=IE`, `VC=VCC-IC*RC`, `VCE=VC-VE` and never uses `beta`. `compare` computes `beta_re_over_r2 = beta*RE/R2`, `rule_satisfied = beta_re_over_r2 >= 10`, `delta_*_pct = abs(a-b)/abs(b)*100` (both `None` when the denominator is 0), and `approximation_valid = rule_satisfied and exact.region == "active" and approx.region == "active"`.

- [ ] **Step 4: Run the full suite, then commit**

Run: `.venv/Scripts/python -m unittest discover -s tests -v`
Expected: 6 tests, OK.

```bash
git add bias/calculator.py tests/test_calculator.py
git commit -m "feat: independent approximate calculation and comparison"
```

---

### Task 4: Input validation

**Files:**
- Create: `bias/validation.py`, `tests/test_validation.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `bias.validation.Inputs` frozen dataclass with `VCC, R1, R2, RC, RE, beta, VBE: float`; `bias.validation.FIELDS: tuple[str, ...] = ("VCC","R1","R2","RC","RE","beta","VBE")`; `bias.validation.parse_inputs(form: Mapping[str, str]) -> tuple[Inputs | None, list[str]]`. Task 5 calls `parse_inputs(request.form)`.

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from bias.validation import parse_inputs

VALID = {"VCC": "12", "R1": "47000", "R2": "10000", "RC": "2200",
         "RE": "1000", "beta": "150", "VBE": "0.7"}


class ValidationTest(unittest.TestCase):
    def test_valid_form(self):
        inputs, errors = parse_inputs(VALID)
        self.assertEqual(errors, [])
        self.assertAlmostEqual(inputs.R1, 47000.0)

    def test_missing_field_gives_message_not_keyerror(self):
        inputs, errors = parse_inputs({k: v for k, v in VALID.items() if k != "R2"})
        self.assertIsNone(inputs)
        self.assertTrue(any("R2" in e for e in errors))

    def test_non_numeric_text(self):
        inputs, errors = parse_inputs({**VALID, "R1": "47k"})
        self.assertIsNone(inputs)
        self.assertTrue(any("R1" in e and "number" in e for e in errors))

    def test_non_positive_resistance_and_beta(self):
        inputs, errors = parse_inputs({**VALID, "RC": "0", "RE": "0", "beta": "0"})
        self.assertIsNone(inputs)
        self.assertEqual(len(errors), 2)   # RE and beta; RC=0 is legal
        self.assertTrue(any("RE" in e for e in errors))
```

- [ ] **Step 2: Run to confirm they fail**

Run: `.venv/Scripts/python -m unittest discover -s tests -k validation -v`
Expected: FAIL — `bias.validation` missing.

- [ ] **Step 3: Implement `parse_inputs`**

For each name in `FIELDS`: missing/blank → `"<name> must be a number"`; `float()` failure → same message; non-finite (`math.isfinite` false) → `"<name> must be a finite number"`. Then range checks: `VCC > 0`, `R1 > 0`, `R2 > 0`, `RC >= 0`, `RE > 0`, `beta > 0`, `VBE >= 0`, each with the wording from the spec §8. Return `(Inputs(...), [])` only when `errors` is empty, else `(None, errors)`.

- [ ] **Step 4: Run the full suite, then commit**

Run: `.venv/Scripts/python -m unittest discover -s tests -v`
Expected: 10 tests, OK.

```bash
git add bias/validation.py tests/test_validation.py
git commit -m "feat: validate and parse user input"
```

---

### Task 5: Flask web layer

**Files:**
- Create: `app.py`, `templates/base.html`, `templates/index.html`, `static/style.css`, `tests/test_routes.py`

**Interfaces:**
- Consumes: `parse_inputs` (Task 4), `solve_exact`, `solve_approximate`, `compare` (Tasks 1–3).
- Produces: `app.create_app() -> flask.Flask` and module-level `app`; routes `GET /` and `POST /calculate`; Jinja filters `ma`, `ua`, `volts`, `pct`.

- [ ] **Step 1: Write the failing HTTP tests**

```python
import unittest
from app import create_app

VALID = {"VCC": "12", "R1": "47000", "R2": "10000", "RC": "2200",
         "RE": "1000", "beta": "150", "VBE": "0.7"}


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_index_shows_form(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'name="VCC"', r.data)

    def test_post_computes_and_renders(self):
        r = self.client.post("/calculate", data=VALID)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"1.324", r.data)      # IC in mA
        self.assertIn(b"7.755", r.data)      # VCE in V
        self.assertIn(b"Active", r.data)

    def test_post_rejects_bad_input_without_crashing(self):
        r = self.client.post("/calculate", data={**VALID, "R1": "abc"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"R1 must be a number", r.data)
        self.assertNotIn(b"Traceback", r.data)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `.venv/Scripts/python -m unittest discover -s tests -k routes -v`
Expected: FAIL — `app` module missing.

- [ ] **Step 3: Implement `create_app` and the templates**

`app.py`: `create_app()` builds `Flask(__name__)`, registers filters (`ma`: value*1000 formatted `:.3f`; `ua`: value*1e6 `:.3f`; `volts`: `:.3f`; `pct`: `:.2f` or `"—"` for `None`), `GET /` renders `index.html` with `defaults` and `errors=[]`, `POST /calculate` calls `parse_inputs`, re-renders with `errors` and the submitted `values` when invalid, otherwise computes `exact`, `approx`, `cmp` and renders with all of them. Module level: `app = create_app()`.

`index.html` extends `base.html`: a `<form method="post" action="/calculate">` with seven labelled number inputs named exactly `VCC, R1, R2, RC, RE, beta, VBE`, an error list when `errors`, a results `<table>` showing VB/VE/VC/VCE in V and IB (mA and µA)/IC/IE in mA, a region banner, `IC_sat` in saturation, and a comparison `<table>` with exact vs approximate, both Δ% values, `β·RE/R2`, and one of "Approximation valid" / "Approximation not valid" / "Model not valid outside the active region". `style.css` gives a readable single-column layout, ~70ch, tabular numbers.

- [ ] **Step 4: Run the full suite, then commit**

Run: `.venv/Scripts/python -m unittest discover -s tests -v`
Expected: 13 tests, OK.

```bash
git add app.py templates/ static/ tests/test_routes.py
git commit -m "feat: Flask routes, result page and comparison table"
```

---

### Task 6: README, reproducibility check and push

**Files:**
- Create: `README.md`
- Modify: `.gitignore` only if a generated file is missing from it

**Interfaces:**
- Consumes: everything.
- Produces: a fresh-clone reproduction path and the GitHub commit for A7.

- [ ] **Step 1: Write `README.md`**

Sections: what it does (one paragraph), formula summary (the seven equations), setup (`python -m venv .venv`, activation for PowerShell and POSIX, `pip install -r requirements.txt`), run (`python -m flask --app app run --debug`, open `http://127.0.0.1:5000/`), test (`python -m unittest discover -s tests -v`), a worked example table with the Task 1 numbers, a note that the debug server is local-only, and an A1–A7 acceptance table mapping each item to the file or test that satisfies it.

- [ ] **Step 2: Verify from a clean environment**

Run: `.venv/Scripts/python -m unittest discover -s tests -v` then start the server and open `/` and a valid POST in the browser.
Expected: all tests OK; page shows IC = 1.324 mA, VCE = 7.755 V, "Active", and a comparison table with ΔIC ≈ 6.16 %.

- [ ] **Step 3: Check the index before committing**

```bash
git status
git diff --staged --stat
```

Expected: no `.venv/`, no `__pycache__/`, no `.env`.

- [ ] **Step 4: Commit and push**

```bash
git add README.md
git commit -m "docs: setup, run, test and acceptance mapping"
git remote add origin <STUDENT_REPO_URL>
git push -u origin main
```

`<STUDENT_REPO_URL>` is supplied by the student at execution time; the repository must be created on GitHub first (no `gh` CLI on this machine).

---

## Self-Review

**Spec coverage:** §7 model → Tasks 1–3; §8 validation → Task 4; §9 web surface → Task 5; §10 layout → all tasks; §11 test plan → E1–E5 in Tasks 1–3, V1–V5 in Task 4, H1–H3 in Task 5; §12 A1–A7 → Tasks 5–6.

**Step scan:** each step names one file, one command, or one function body; no step says "handle edge cases".

**Type consistency:** `solve_exact`/`solve_approximate` keep the same keyword names (`VCC, R1, R2, RC, RE, beta, VBE`) across Tasks 1–5; `OperatingPoint.IC_sat` is added in Task 2 and read in Task 5; `Comparison` field names are used verbatim in the template.

**Review Focus coverage:** missing field → Task 4 `test_missing_field_gives_message_not_keyerror`; non-numeric text → Task 4 `test_non_numeric_text`; `RC=0` → Task 4 `test_non_positive_resistance_and_beta` (asserts RC=0 is accepted) plus Task 1's formula; negative `VCE` percentages → Task 3 `test_approximation_never_valid_outside_active_region`; `beta < 1` → Task 5's page renders any finite value, covered by Task 3's active-path comparison test.
