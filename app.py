"""Flask entry point: routes only, engineering lives in bias/ and spice_engine."""

import charts
from flask import Flask, render_template, request

from bias.calculator import (VCE_SAT, compare, solve_approximate, solve_divider,
                             solve_emitter, solve_exact, solve_fixed)
from bias.validation import (MODE_NAMES, parse_inputs, unknown_mode_error,
                             validate_mode)
from spice_engine import (ANALYSES, ANALYSIS_NAMES, SIM_DEFAULTS, SIM_FIELDS,
                          SpiceError, engine_info, parse_params, run_analysis)

# The form takes resistors in kOhm; the engineering layer works in Ohm.
KOHM_FIELDS = ("R1", "R2", "RC", "RE", "RB")

MODE_DEFAULTS = {
    "divider": {"VCC": "12", "R1": "100", "R2": "22", "RC": "2.2",
                "RE": "1.0", "beta": "100", "VBE": "0.70"},
    "fixed": {"VCC": "12", "RB": "1000", "RC": "2.2",
              "beta": "100", "VBE": "0.70"},
    "emitter": {"VCC": "12", "RB": "1000", "RC": "2.2", "RE": "1.0",
                "beta": "100", "VBE": "0.70"},
}

FIELDS = {
    "divider": (
        ("VCC", "VCC (Supply Voltage)", "V"),
        ("R1", "R1 (Upper Divider)", "k\u03a9"),
        ("R2", "R2 (Lower Divider)", "k\u03a9"),
        ("RC", "RC (Collector Resistor)", "k\u03a9"),
        ("RE", "RE (Emitter Resistor)", "k\u03a9"),
        ("beta", "\u03b2 (Current Gain)", ""),
        ("VBE", "VBE (Base-Emitter Voltage)", "V"),
    ),
    "fixed": (
        ("VCC", "VCC (Supply Voltage)", "V"),
        ("RB", "RB (Base Resistor)", "k\u03a9"),
        ("RC", "RC (Collector Resistor)", "k\u03a9"),
        ("beta", "\u03b2 (Current Gain)", ""),
        ("VBE", "VBE (Base-Emitter Voltage)", "V"),
    ),
    "emitter": (
        ("VCC", "VCC (Supply Voltage)", "V"),
        ("RB", "RB (Base Resistor)", "k\u03a9"),
        ("RC", "RC (Collector Resistor)", "k\u03a9"),
        ("RE", "RE (Emitter Resistor)", "k\u03a9"),
        ("beta", "\u03b2 (Current Gain)", ""),
        ("VBE", "VBE (Base-Emitter Voltage)", "V"),
    ),
}

MODE_CHOICES = tuple((key, MODE_NAMES[key]) for key in ("fixed", "emitter", "divider"))

SIM_CHOICES = tuple((key, ANALYSIS_NAMES[key]) for key in ANALYSES)

# Display-only reminder of which base-loop equation the mode uses. The
# numbers are still computed only in bias/calculator.py; this dict keeps the
# equations out of the template.
MODE_FORMULAS = {
    "fixed": "IB = (VCC \u2212 VBE) / RB   \u00b7   VE = 0",
    "emitter": "IB = (VCC \u2212 VBE) / (RB + (\u03b2 + 1)\u00b7RE)",
    "divider": ("IB = (VTH \u2212 VBE) / (RTH + (\u03b2 + 1)\u00b7RE)   \u00b7   "
                "VTH = VCC\u00b7R2/(R1+R2)"),
}


def to_ohms(form):
    """Return a plain dict of SI values; leave unparseable text for validation."""
    data = {key: form.get(key) for key in form}
    for name in KOHM_FIELDS:
        raw = data.get(name)
        if raw is None:
            continue
        try:
            data[name] = repr(float(raw) * 1000.0)
        except (TypeError, ValueError):
            pass
    return data


def create_app() -> Flask:
    app = Flask(__name__)

    app.jinja_env.filters["ma"] = lambda amps: f"{amps:.2f}"
    app.jinja_env.filters["ua"] = lambda amps: f"{amps:.1f}"
    app.jinja_env.filters["volts"] = lambda v: f"{v:.2f}"
    app.jinja_env.filters["volts3"] = lambda v: f"{v:.3f}"
    app.jinja_env.filters["pct"] = (
        lambda p: "\u2014" if p is None else f"{p:.2f}")

    def sim_context(**overrides):
        context = {
            "sim_fields": SIM_FIELDS,
            "sim_values": SIM_DEFAULTS,
            "engine": engine_info(),
            "analysis_choices": SIM_CHOICES,
            "sim_analysis": "dc",
            "sim_result": None,
            "sim_errors": [],
            "sim_detail": "",
        }
        context.update(overrides)
        return context

    def render(mode, fields, values, errors, result, **sim):
        return render_template(
            "index.html", mode=mode, mode_name=MODE_NAMES.get(mode),
            mode_choices=MODE_CHOICES, fields=fields, values=values,
            errors=errors, result=result, vce_sat=VCE_SAT,
            formula=MODE_FORMULAS.get(mode), **sim_context(**sim),
        )

    @app.get("/")
    def index():
        raw = request.args.get("mode", "")
        mode = "divider" if raw == "" else validate_mode(raw)
        if mode is None:
            return render(None, (), {}, [unknown_mode_error(raw)], None)
        return render(mode, FIELDS[mode], MODE_DEFAULTS[mode], [], None)

    @app.post("/calculate")
    def calculate():
        raw = request.form.get("mode", "")
        mode = validate_mode(raw)
        if mode is None:
            return render(None, (), dict(request.form),
                          [unknown_mode_error(raw)], None)

        inputs, errors = parse_inputs(to_ohms(request.form), mode)
        if errors:
            return render(mode, FIELDS[mode], dict(request.form), errors, None)

        if mode == "divider":
            point = solve_divider(inputs.VCC, inputs.R1, inputs.R2, inputs.RC,
                                  inputs.RE, inputs.beta, inputs.VBE)
            exact = solve_exact(inputs.VCC, inputs.R1, inputs.R2, inputs.RC,
                                inputs.RE, inputs.beta, inputs.VBE)
            approx = solve_approximate(inputs.VCC, inputs.R1, inputs.R2,
                                       inputs.RC, inputs.RE, inputs.beta,
                                       inputs.VBE)
            cmp = compare(exact, approx, inputs.beta, inputs.RE, inputs.R2)
        elif mode == "fixed":
            point = solve_fixed(inputs.VCC, inputs.RB, inputs.RC,
                                inputs.beta, inputs.VBE)
            cmp = None
        else:
            point = solve_emitter(inputs.VCC, inputs.RB, inputs.RC, inputs.RE,
                                  inputs.beta, inputs.VBE)
            cmp = None

        return render(mode, FIELDS[mode], dict(request.form), [],
                      {"mode": mode, "point": point, "cmp": cmp})

    @app.post("/simulate")
    def simulate():
        analysis = request.form.get("analysis", "dc")
        mode = validate_mode(request.form.get("mode", "divider")) or "divider"
        submitted = dict(request.form)

        if analysis not in ANALYSES:
            return render(mode, FIELDS[mode], MODE_DEFAULTS[mode], [], None,
                          sim_analysis=analysis, sim_values=submitted,
                          sim_errors=[f"Unknown analysis '{analysis}'."])

        params, errors = parse_params(request.form)
        if errors:
            return render(mode, FIELDS[mode], MODE_DEFAULTS[mode], [], None,
                          sim_analysis=analysis, sim_values=submitted,
                          sim_errors=errors)

        try:
            result = run_analysis(analysis, params)
        except SpiceError as exc:
            return render(mode, FIELDS[mode], MODE_DEFAULTS[mode], [], None,
                          sim_analysis=analysis, sim_values=submitted,
                          sim_errors=[exc.message], sim_detail=exc.detail)

        result["charts"] = {}
        if analysis == "ac":
            result["charts"]["gain"] = charts.bode_gain_chart(result["ac"])
            result["charts"]["phase"] = charts.bode_phase_chart(result["ac"])
        elif analysis == "tran":
            result["charts"]["tran"] = charts.transient_chart(result["tran"])
        else:
            # Same circuit, Lab 3 equations, for a labelled cross-check.
            result["analytical"] = solve_divider(
                params["VCC"], params["R1"], params["R2"], params["RC"],
                params["RE"], 100.0, 0.70)
            result["analytical_note"] = (
                "Analytical column: Lab 3 model, \u03b2 = 100 and VBE = 0.70 V "
                "constant. The SPICE run uses the 2N3904 card (BF = 416), so "
                "the two sets are expected to differ; neither is a copy of "
                "the other.")

        return render(mode, FIELDS[mode], MODE_DEFAULTS[mode], [], None,
                      sim_analysis=analysis, sim_values=submitted,
                      sim_result=result)

    return app


app = create_app()
