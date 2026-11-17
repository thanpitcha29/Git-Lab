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

## Notes for the report

- Unknown mode is rejected rather than defaulting to Divider: POSTing
  `mode=bogus` returns `Unknown bias mode 'bogus'. Choose fixed, emitter or divider.`
- Result keys and units are identical across the three modes
  (`vb_v, ve_v, vc_v, vce_v, ic_ma, ib_ma, ib_ua, ie_ma, region, warning`).
- The Divider comparison table (β-free approximation) is unchanged from Lab 02.
- Existing `unittest` suite still passes: 18 tests.
