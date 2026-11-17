# Lab 03 — Three Bias Modes Implementation Plan

Date: 2026-11-17 · Status: **awaiting student approval**

Extends the Lab 02 app. The Divider result must stay exactly as it is.

## What changes

| File | Change |
|---|---|
| `bias/calculator.py` | Add `solve_fixed(...)`, `solve_emitter(...)` and a canonical `solve_divider(...)` wrapper around the existing `solve_exact`. Add a shared `_operating_point()` that turns IB into the result dict and computes region + warning. `solve_exact`, `solve_approximate`, `compare`, `OperatingPoint`, `IC_sat` stay untouched so the existing tests keep working. |
| `bias/validation.py` | Add `MODES` map, `validate_mode()`, and make `parse_inputs(form, mode)` validate **only** the fields that mode needs. Add `RB > 0`. Unknown mode returns an error, never defaults to Divider. |
| `app.py` | `if / elif` dispatch on the posted `mode`; `to_ohms` now also converts `RB`; `GET /?mode=...` renders that mode's form; results always come from the current POST (no stale result). |
| `templates/index.html` | Mode selector (same form, `formmethod="get"` so switching reloads without JavaScript), only the relevant fields shown, result header and error banner name the selected mode, warning block for IB ≤ 0 / VCE ≤ 0.2 V. Schematic switches with the mode. |
| `static/style.css` | Mode selector, warning block, per-mode field layout. |
| `opencode.json` (new, project root) | Playwright MCP server block (V2 `mcp.servers`). |
| `docs/validation.md` (new) | A1–A5 table with expected values, observed values, method and status. |

No equations in HTML, no rebuild, no new unittest files.

## Canonical result (same keys for all three modes)

```python
{
  "mode": "fixed" | "emitter" | "divider",
  "ib_ma": float, "ib_ua": float,
  "ic_ma": float, "ie_ma": float,
  "vb_v": float, "ve_v": float, "vc_v": float, "vce_v": float,
  "vth_v": float | None, "rth_ohm": float | None,   # divider only
  "region": "active" | "cutoff" | "saturation",
  "ic_sat_ma": float | None,
  "warning": str | None,
}
```

## Formulas (from the lab sheet, SI units)

| Mode | IB | VE |
|---|---|---|
| Fixed | `(VCC − VBE) / RB` | `0 V` |
| Emitter | `(VCC − VBE) / (RB + (β + 1)·RE)` | `IE·RE` |
| Divider | `(VTH − VBE) / (RTH + (β + 1)·RE)` | `IE·RE` |

then `IC = β·IB`, `IE = (β+1)·IB`, `VB = VE + VBE`, `VC = VCC − IC·RC`, `VCE = VC − VE`.

`VTH = VCC·R2/(R1+R2)`, `RTH = R1·R2/(R1+R2)`.

Warning when `IB <= 0` or `VCE <= 0.2 V` (Forward Active model not usable); no cutoff/saturation correction is computed.

## Reference values (computed independently with exact rationals)

Common: `VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V`

| Case | Inputs | IC (mA) | VCE (V) |
|---|---|---|---|
| A1 Divider | R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ | 1.229858 | 8.052155 |
| A2 Fixed | RB = 1 MΩ (1000 kΩ) | 1.130000 | 9.514000 |
| A3 Emitter | RB = 1 MΩ, RE = 1 kΩ | 1.026340 | 8.705450 |
| A4 Emitter | RB = 1 MΩ, RE = 2 kΩ | 0.940100 | 8.032779 |
| A5 Fixed | RB = 0 | error, no result | error, no result |

A4 prediction: RE doubles → IB falls → **IC decreases** (1.0263 → 0.9401 mA).

## Verification

1. `python -m unittest discover -s tests -v` — the existing 17 tests must still pass.
2. Browser acceptance A1–A5 at `http://127.0.0.1:5000/`, tolerance 0.01 mA (IC) and 0.02 V (VCE), recorded in `docs/validation.md`.
3. Playwright MCP is configured in `opencode.json`; if Node/npx is unavailable the same cases are run with the OpenCode Browser tool and the method is recorded as such.
