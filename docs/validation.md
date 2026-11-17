# Lab 03 — Browser acceptance A1–A5

Date: 2026-11-17
App: `http://127.0.0.1:5000/` (Flask debug server, `python -m flask --app app run --debug`)

## Method

| Item | Value |
|---|---|
| Playwright MCP | **NOT RUN** — `node` and `npx` are not installed on this machine (`node --version` → command not found), so the MCP server cannot start. |
| Actual method | **OpenCode Browser** (the in-app Chromium browser tool): real page load, real form fill, real button click, real HTTP POST. |
| Manual fallback | Not needed. |

Form values were set in the page and submitted by clicking the real
**Calculate DC Bias** button; results were read back from the rendered page
after each submit (never reused from a previous round).

## Reference values (independent of the app)

Computed with exact rational arithmetic from the lab sheet's equations, not
from the program under test. Common inputs: `VCC = 12 V, RC = 2.2 kΩ,
β = 100, VBE = 0.70 V`.

Tolerance: `IC` within 0.01 mA, `VCE` within 0.02 V of the unrounded
reference. The page displays 2 decimals.

## Results

| ID | Mode | Inputs (as typed on the form) | Expected (reference) | Observed | Status |
|---|---|---|---|---|---|
| A1 | Voltage Divider Bias | R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ | IC = 1.229858 mA · VCE = 8.052155 V | IC = 1.23 mA · VCE = 8.05 V | **PASS** |
| A2 | Fixed Bias | RB = 1000 kΩ (1 MΩ) | IC = 1.130000 mA · VCE = 9.514000 V | IC = 1.13 mA · VCE = 9.51 V | **PASS** |
| A3 | Emitter Bias | RB = 1000 kΩ, RE = 1 kΩ | IC = 1.026340 mA · VCE = 8.705450 V | IC = 1.03 mA · VCE = 8.71 V | **PASS** |
| A4 | Emitter Bias | RB = 1000 kΩ, RE = **2 kΩ** | IC = 0.940100 mA · VCE = 8.032779 V | IC = 0.94 mA · VCE = 8.03 V | **PASS** |
| A5 | Fixed Bias | RB = 0 | Validation error naming RB, page alive, no result shown | `Mode: Fixed Bias — check these inputs / RB must be greater than 0 Ω`, no result table rendered | **PASS** |

### A1 — Divider unchanged from Lab 02

Same inputs as the Lab 02 default page; IC and VCE match the Lab 02 values
(IC 1.23 mA, VCE 8.05 V) and the reference.

### A2 — Fixed needs no RE

The form shows only VCC, RB, RC, β, VBE in Fixed mode; RE is not required and
not validated. `VE = 0 V`, so `VB = VBE = 0.70 V` and `VCE = VC = 9.51 V`.

### A3 — Emitter uses RE

`IB = (VCC − VBE) / (RB + (β+1)·RE)`; the RE field is present and used:
`VE = 1.04 V`, `VCE = 8.71 V`.

### A4 — prediction and check

Prediction before running: doubling RE increases the denominator of IB, so IB
and therefore IC must **decrease**.
Observed: IC 1.03 mA (A3) → **0.94 mA** (A4), VCE 8.71 V → 8.03 V.
Direction matches the prediction.

### A5 — invalid input vs. unusable model

`RB = 0` is an **input error**, reported by the Flask validation layer
(`bias/validation.py`), not a model warning. The page returns HTTP 200, shows
the message, and renders no result table, so the previous round's numbers are
not mistaken for this round's.

## Evidence

`docs/evidence-a2-fixed-bias.jpg` — full-page screenshot of case A2 as rendered in
the browser: Fixed Bias mode selected, RB = 1000 kΩ, result card showing
IC = 1.13 mA and VCE = 9.51 V.

## Independent reference (new mode)

Case A2, Fixed Bias, `VCC = 12 V, RB = 1 MΩ = 1,000,000 Ω, RC = 2.2 kΩ = 2200 Ω,
β = 100, VBE = 0.70 V`.

```
IB  = (VCC - VBE) / RB = (12 - 0.70) / 1,000,000 = 11.3 µA
IC  = β · IB = 100 × 11.3 µA = 1.13 mA
IE  = (β + 1) · IB = 1.1413 mA
VE  = 0 V (emitter grounded)      VB = VE + VBE = 0.70 V
VC  = VCC - IC·RC = 12 - 1.13 mA × 2200 Ω = 9.514 V
VCE = VC - VE = 9.514 V
```

All values computed with exact rational arithmetic before the app was run.

## Who did what

| Part | Done by |
|---|---|
| `bias/calculator.py` — `solve_fixed`, `solve_emitter`, `solve_divider`, `_point` | AI |
| `bias/validation.py` — mode map, per-mode field checks, `RB > 0` | AI |
| `app.py` — `if / elif` mode dispatch, kΩ → Ω conversion in `to_ohms` | AI |
| `templates/index.html`, `static/style.css` — mode selector, per-mode fields, result/warning layout | AI |
| Independent reference values (A1–A5) | AI computed them from the lab sheet's equations; **the student must re-verify at least one case by hand** |
| A1–A5 browser runs and observed values | AI drove the browser; **the student must repeat at least one case themselves** |
| Choice of which function runs and where units are converted | `app.py` `calculate()` picks `solve_fixed` / `solve_emitter` / `solve_divider`; `to_ohms()` converts kΩ → Ω once, before validation |

## Notes for the report

- Unknown mode is rejected rather than defaulting to Divider: POSTing
  `mode=bogus` returns `Unknown bias mode 'bogus'. Choose fixed, emitter or divider.`
- Result keys and units are identical across the three modes
  (`vb_v, ve_v, vc_v, vce_v, ic_ma, ib_ma, ib_ua, ie_ma, region, warning`).
- The Divider comparison table (β-free approximation) is unchanged from Lab 02.
- Existing `unittest` suite still passes: 18 tests.

## Closing question

> ถ้าตัวเลขคำนวณมือถูก แต่เปลี่ยน RE แล้วผลบนหน้าเว็บไม่เปลี่ยน จะตรวจค่าที่ส่งจากฟอร์ม
> และค่าที่เข้าไปในฟังก์ชันอย่างไร?

Check the value at each hop instead of guessing, because four different hops can
lose it:

1. **Browser → server (what the form sent).** DevTools → Network → the
   `POST /calculate` request → *Payload*. `RE` must appear with the newly typed
   value, and `mode` must be the mode whose form contains RE. If `mode` is
   wrong, the server ignores RE by design and the numbers cannot change.
2. **Raw form → SI values (conversion).** In `app.py`, print/log
   `request.form` and then `to_ohms(request.form)`. `RE = 2` must become
   `'2000.0'`. Two mistakes show up here: the field missing from
   `KOHM_FIELDS` (handled as 2 Ω instead of 2 kΩ) or a double conversion
   (2,000,000 Ω). Values must change here — if they do not, the problem is in
   step 1.
3. **Validation → `Inputs` (the value the function receives).** Log
   `parse_inputs(...)` → `inputs.RE`. It must not be `None`, which would mean
   `MODES[mode]` never listed RE for that mode and the field was dropped.
4. **Dispatch → function (which equation ran, with which argument).** In
   `calculate()` confirm the branch: `fixed` calls `solve_fixed()` — which takes
   **no RE at all** and therefore *must* not react to RE; `emitter` calls
   `solve_emitter(VCC, RB, RC, RE, beta, VBE)`; `divider` calls
   `solve_divider(VCC, R1, R2, RC, RE, beta, VBE)`. A wrong branch (or swapped
   positional arguments, e.g. RE landing in RC) is the classic cause of
   "input changes, result doesn't".
5. **Function → page (what was rendered).** In the browser, hard-reload and
   read the `mode-line`/result table, and check the response itself
   (`Invoke-WebRequest -Method POST`) so a stale page or an error branch that
   keeps the previous result cannot be mistaken for a new computation.
6. **Pin it with a check.** Reproduce the same call in a REPL —
   `solve_emitter(12, 1e6, 2200, 2000, 100, 0.7)` — and compare IC/VCE with the
   page. Then add/keep a regression test that submits two different RE values
   and asserts IC changes, so the missing-field bug cannot come back silently.

The rule of thumb: verify the payload first, then the converted value, then the
argument the function actually received — never only the final number on screen.

