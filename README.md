# Git-Lab

Repository for ENG29 2121 labs.

---

# Lab 04: BJT CE Amplifier Simulator

A Flask web app that keeps the three Lab 03 analytical DC-bias modes
(**Fixed / Emitter / Divider**) and adds a **real ngspice simulation** of one
reference common-emitter voltage-divider stage:

- **DC** — `.op` operating point (VB, VE, VC, VCE, IC, IB, IE, region) plus a
  separate, clearly labelled Lab 03 analytical cross-check.
- **AC** — `.ac` sweep, gain and phase Bode plots referenced to the source,
  with gain at 1 kHz and the lower −3 dB corner.
- **Transient** — `.tran` Vin/Vout versus time, peak values, gain and inversion.

Every plotted point comes from an ngspice `wrdata` file written during that
request. Nothing is hard-coded, no success value is faked, and engine errors are
shown with their netlist/log detail. The engine status (Running / Success /
Error), the model card, the command, the run directory and the log tail are
visible on the page.

## Submission

| Item | Value |
|---|---|
| Repository | <https://github.com/thanpitcha29/Git-Lab> |
| Branch | `main` |
| Lab 04 implementation commit | `660d7d3a369a16c2d9056a44829b2f86ca7f12c5` |
| Lab 03 commit (previous submission) | `3b978ff` |
| Lab 04 B1–B8 acceptance, evidence, before/after screenshots, AI/student split | [`docs/validation.md`](docs/validation.md) |
| Before / after UI screenshots | [`docs/captures/before-b8-desktop.png`](docs/captures/before-b8-desktop.png), [`docs/captures/after-b8-desktop.png`](docs/captures/after-b8-desktop.png), mobile counterparts in the same folder |
| Student reflection | [`REFLECTION.md`](REFLECTION.md) |

AI built the ngspice adapter, SVG charts, simulation route/UI, the 20 new tests
and the Impeccable polish. The student must hand-check at least one DC case
against the lab equations, repeat at least one B1–B8 browser run, and fill in
`REFLECTION.md`.

## Requirements and installation

### Python

Python 3.10+ (verified with 3.12.7) and Flask 3; no other Python plotting
dependency is needed — charts are server-side SVG.

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

### ngspice (required for Lab 04 simulation)

- **Windows (portable, used for this submission):** download the ngspice 47
  Win64 zip, extract it to `.tools/ngspice/`, and keep the console binary at
  `.tools/ngspice/Spice64/bin/ngspice_con.exe`. `.tools/` is gitignored.
- **Linux:** `sudo apt-get install ngspice`
- **macOS:** `brew install ngspice`

If ngspice is installed elsewhere, set `NGSPICE_BIN` to the console executable
before starting Flask. With no engine available, the page reports an explicit
engine error and renders no result — it never substitutes fabricated values.
The BJT model is a 2N3904 card embedded in `spice_engine.py` (a stand-in because
no starter kit was supplied); swap it there if the course provides its own card.

### Browser checks (optional)

Node.js and `playwright-core` plus an installed Chrome are needed only to rerun
the acceptance script. This session used portable Node 22.23.5 in `.tools/node`
and `playwright-core` 1.65.1 in `.tools/browser`; neither is committed.

## Run

```bash
python -m flask --app app run --port 5000 --no-debugger --no-reload
```

Open <http://127.0.0.1:5000/>.

The Flask development server binds to localhost only. Do not expose it to a
network, and never commit `.venv/`, `.tools/`, `.env`, API keys or credentials.
Templates are not auto-reloaded with `--no-reload`: restart the server after
editing `templates/` or `static/`.

## Using the simulator

1. Choose **DC operating point (.op)**, **AC sweep (.ac)** or **Transient
   (.tran)**.
2. Edit the grouped inputs: **Circuit** (kΩ / µF) and **Source** (mV / Hz).
   Defaults: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ,
   Cin = Cout = 10 µF, source 10 mV peak at 1 kHz.
3. Click **Run Simulation**. A status pill, the ngspice version, the command,
   the run directory, the netlist and the log tail are shown with the results.
4. Invalid values (e.g. `RE = 0`) and engine failures are reported as
   `Simulation stopped — no result shown`; the previous run's numbers are not
   reused.

The DC result includes a **Cross-check — Lab 3 analytical model** table. It uses
β = 100 and constant VBE = 0.70 V, while SPICE uses the 2N3904 card (BF = 416);
the differences are expected and explained on the page. AC phase is unwrapped
degrees; the gain is `vdb(out) − vdb(src)`. The AC sweep is 1 Hz – 100 MHz, so an
upper −3 dB point above that range is labelled `above sweep (> 100 MHz)` rather
than guessed.

## Test

```bash
python -m unittest discover -s tests -v
```

38 tests: the original Lab 02/03 engineering, validation and HTTP tests plus
20 Lab 04 tests for unit conversion, netlist directives, `wrdata` parsing,
phase unwrapping, SVG charts and real `.op`/`.ac`/`.tran` runs. Engine tests
skip cleanly when ngspice is not installed.

To reproduce the browser checks, start the server, make Node available on PATH,
and run the committed script with `playwright-core` resolvable:

```powershell
$env:NODE_PATH = "C:\Users\b6827021\Documents\Default Project\.tools\browser\node_modules"
node tests\acceptance.js after
```

It writes `PASS/FAIL` lines plus full-page screenshots into `docs/captures/`.
The recorded runs are in `docs/captures/*-results.txt`.

## Lab 03 — retained analytical DC bias

Three single-supply topologies share one DC model and one result shape:
**Fixed Bias**, **Emitter Bias** and **Voltage Divider Bias**. The Lab 03 form
is unchanged; it still converts kΩ → Ω once in `app.py` `to_ohms()`.

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

The independent β-free check drops base current (stiff divider):

```
VB = VTH ,  VE = VB − VBE ,  IE = VE / RE ,  IC ≈ IE ,  VCE = VCC − IC·(RC + RE)
```

The two are compared with a percentage difference and the stiffness rule
`β·RE ≥ 10·R2`. Region rules (`VCE_SAT = 0.2 V`): cutoff when `VTH ≤ VBE`;
saturation when `VCE < 0.2 V`; active otherwise.

### Lab 03 acceptance mapping

| Item | Where |
|---|---|
| A1 · Divider still correct | `solve_divider()` wraps `solve_exact()`; `docs/validation.md` A1 / B1a |
| A2 · Fixed bias (no RE) | `solve_fixed()`; `app.py` `elif mode == "fixed"` |
| A3 · Emitter bias uses RE | `solve_emitter()`; `MODES["emitter"]` |
| A4 · Doubling RE lowers IC | observed 1.03 → 0.94 mA in `docs/validation.md` A4 |
| A5 · Bad input rejected | `bias/validation.py` (`RB > 0`); HTTP test |
| Same keys/units for all modes | `_point()`: `vb_v … ie_ma`, `region`, `warning` |
| Unknown mode rejected | `validate_mode()` + `unknown_mode_error()` |

### Worked Lab 03 example

`VCC = 12 V, R1 = 47 kΩ, R2 = 10 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 150, VBE = 0.7 V`
→ IC 1.324 mA, VCE 7.755 V, active; approximate IC 1.405 mA, VCE 7.503 V.

## Layout

```
app.py                  Flask routes and unit formatting (Lab 03 + /simulate)
bias/calculator.py      Lab 03 DC model (no Flask imports)
bias/validation.py      form parsing and range rules
spice_engine.py         ngspice adapter: netlist, run, parse, errors
charts.py               server-side SVG charts from real ngspice data
templates/              analytical form + simulation card
static/style.css        lab-style layout, charts, mobile tweaks
tests/                  unittest suite + acceptance.js (Playwright)
docs/validation.md      A1–A5 and B1–B8 evidence
docs/captures/          before/after screenshots and result logs
REFLECTION.md           student reflection (to be completed)
```

## Assumptions

- Lab 03: VBE and β are constant, no Early effect or leakage; the transistor is
  ideal outside the active region; resistors are temperature-independent.
- Lab 04: one fixed CE topology with a documented 2N3904 stand-in card; units
  are converted once at the form boundary (kΩ/µF/mV → Ω/F/V).
- The Flask development server is for local teaching use only.
