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

---

# Lab 04 — BJT CE Amplifier Simulator (B1–B8)

Date: 2026-11-24 · Repository: <https://github.com/thanpitcha29/Git-Lab> ·
Branch: `main` · Implementation commit:
`660d7d3a369a16c2d9056a44829b2f86ca7f12c5` (also recorded in
[`README.md`](../README.md)).

App: `http://127.0.0.1:5000/` (Flask 3, `python -m flask --app app run --port
5000 --no-debugger --no-reload`). Python 3.12.7. Engine: **ngspice-47**,
portable console binary at `.tools/ngspice/Spice64/bin/ngspice_con.exe`
(gitignored). Browser driver: Chrome + `playwright-core` 1.65.1.

## Method and tool status

| Item | Value |
|---|---|
| Playwright MCP | **NOT RUN** — the MCP server was configured with bare `npx`, which was not on PATH at session start; it cannot be restarted mid-session. Portable Node 22.23.5 was installed later in gitignored `.tools/node`, but the MCP route stayed unavailable. |
| Actual method (substitute) | Direct Playwright script (`.tools/browser/acceptance.js`, local/gitignored): real page load, real field fill, real radio selection, real **Run Simulation** click, real HTTP POST; values read back from the rendered page. |
| Manual fallback | Not needed; every B-case was driven through the UI. |
| Raw evidence | [`before-results.txt`](captures/before-results.txt) (11/11) and [`after-results.txt`](captures/after-results.txt) (12/12). |
| Screenshots | Before polish: [`before-b8-desktop.png`](captures/before-b8-desktop.png), [`before-b8-mobile.png`](captures/before-b8-mobile.png). After polish: [`after-b1-regression.png`](captures/after-b1-regression.png) … [`after-b8-mobile.png`](captures/after-b8-mobile.png). |
| Unit/regression suite | 38 tests, all OK (`python -m unittest discover -s tests -v`). |
| Impeccable | Critique → polish → audit on the running UI; final `impeccable detect --json --changed`: 0 warnings, 1 advisory (faint measurement-grid background, retained deliberately). |

No plotted value is hard-coded. Each request writes a fresh netlist and takes
the data from ngspice's `wrdata` ASCII files in its own `runs/<timestamp>-...`
directory; the netlist, command, run directory and log tail are visible under
**Provenance**. Engine state, per-analysis metrics, units and error text are
rendered from that run's result object.

## Reference circuit and engine facts

- `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`,
  `RL = 10 kΩ`, `Cin = Cout = 10 µF`, source `10 mV peak / 1 kHz`, unbypassed
  emitter resistor. `Vin` is measured at the source before `Cin`; `Vout` at the
  collector after `Cout`.
- No starter kit was supplied, so `spice_engine.py` embeds a documented
  **2N3904** card (BF = 416.4) as a stand-in. The Lab 03 analytical column uses
  β = 100 and constant VBE = 0.70 V, so the two columns are expected to differ;
  they are labelled separately and neither is copied from the other.
- AC: `.ac dec 20 1 100e6` (161 points). Gain = `vdb(out) − vdb(src)`; phase =
  `vp(out) − vp(src)`, converted from radians to degrees and unwrapped for a
  continuous Bode curve. The upper −3 dB corner lies above the 100 MHz sweep,
  so the UI says **above sweep (> 100 MHz)** rather than inventing a value.
- Transient: `.tran` to 0.2 s, 601 points; only the last periods are plotted.

## Results (B1–B8)

| ID | Check | Expected / independent reference | Observed | Status |
|---|---|---|---|---|
| B1a | Lab 03 Divider unchanged | IC 1.23 mA · VCE 8.05 V (`docs/validation.md` A1) | IC 1.23 mA · VCE 8.05 V | **PASS** |
| B1b | Lab 03 Fixed unchanged | IC 1.13 mA · VCE 9.51 V (A2) | IC 1.13 mA · VCE 9.51 V | **PASS** |
| B1c | Lab 03 Emitter unchanged | IC 1.03 mA · VCE 8.71 V (A3) | IC 1.03 mA · VCE 8.71 V | **PASS** |
| B2 | DC `.op` is a real ngspice run | Success pill + ngspice version + operating point from the emitted netlist; analytical Lab 03 values shown only as a labelled comparison | VB 2.004 V, VE 1.333 V, VC 9.087 V, VCE 7.754 V, IC 1.324 mA, IB 8.89 µA, IE 1.333 mA, `active`; netlist/log in provenance | **PASS** |
| B3 | Change `RE` 1 kΩ → 2 kΩ | IC must decrease, VCE must change | IC 1.324 → 0.705 mA; VCE 7.754 → 9.032 V; new `Success` run | **PASS** |
| B4 | AC sweep | Gain and phase vs frequency with Hz/dB/degree axes, referenced to Vin | Gain @1 kHz 4.89 dB (×1.76), fL 1.78 Hz, phase ≈ −83° → −180° → −300°, 161 points, 2 SVG Bode charts | **PASS** |
| B5 | Transient | Vin/Vout vs time, inverted CE output | Vin peak 10.00 mV, Vout peak 17.56 mV, gain ×1.76, `inverted (180°)`, 601 points, 1 SVG chart | **PASS** |
| B6 | Change source 20 mV / 2 kHz | Vin peak must follow the new amplitude | Vin peak 20.00 mV in the new run | **PASS** |
| B7 | Invalid input and engine failure | Input errors and SPICE failures must fail loudly, with no success bar or fake trace | `RE = 0` → `Simulation stopped — no result shown`, `RE must be greater than 0 Ω`, 0 success bars. Forced bad engine (`NGSPICE_BIN=requirements.txt`) → HTTP 200, no success bar, `Could not start ngspice.` plus `[WinError 193] …` detail | **PASS** |
| B8a | Desktop 1280 px | No horizontal page overflow | `document.documentElement.scrollWidth <= innerWidth` | **PASS** |
| B8b | Phone 390 px | No horizontal page overflow | `document.documentElement.scrollWidth <= innerWidth` at 390 × 844, DPR 2 | **PASS** |
| B8c | Phone chart legibility | Wide charts readable without breaking the page | `.chart-scroll` 640 px chart inside 308 px viewport, scrollable; x-title/ticks/legend on separate rows | **PASS** |

### DC cross-check — SPICE vs analytical (B2)

| Quantity | SPICE 2N3904 | Analytical β = 100 | Difference |
|---|---|---|---|
| VB | 2.004 V | 1.942 V | 3.2 % |
| VCE | 7.754 V | 8.052 V | 3.7 % |
| IC | 1.324 mA | 1.230 mA | 7.7 % |

With `RE = 2 kΩ`: SPICE IC 0.705 mA / VCE 9.032 V vs analytical 0.665 mA /
9.192 V (6.0 % / 1.7 %). The difference comes from the device card (BF = 416),
not from a copied or substituted result.

### UI polish and audit

Before polish, the Bode x-axis title collided with its tick labels, the ten
simulation fields were one undifferentiated grid, and the −3 dB fallback text
was vague. After polish: chart tick / axis-title / legend rows are separated,
fields are grouped into **Circuit** and **Source**, the sweep limit is named in
the fallback text, SPICE result rows are right-aligned, mobile charts scroll
inside their card, focus rings and `role`/live-status markup were added, and
the gradient heading and strong grid overlay were toned down. Detector output:
1 advisory (`codex-grid-background`, the deliberately faint measurement grid);
the detector also warns that it cannot resolve the Jinja `url_for()` stylesheet
link, so its colour-rule coverage is incomplete — that is a tool limitation,
not a page error. Impeccable's technical audit checklist was applied manually:
keyboard focus indicators, labelled radio groups/status, escaped SVG labels,
contrast, responsive overflow and no motion that blocks reading.

## Who did what (Lab 04)

| Part | Done by |
|---|---|
| `spice_engine.py`, `charts.py`, simulation routes, template/CSS and 20 new tests | AI |
| Impeccable critique → polish → audit and B1–B8 browser runs | AI |
| Hand-check of the Lab 03 equations/reference values, at least one DC case by hand, and a repeat of at least one B-case in the browser | **Student — still to do** |
| Answers in `REFLECTION.md` | **Student — still to do** |

