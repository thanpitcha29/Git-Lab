"""Flask entry point: routes only, engineering lives in bias/."""

from flask import Flask, render_template, request

from bias.calculator import VCE_SAT, compare, solve_approximate, solve_exact
from bias.validation import parse_inputs

DEFAULTS = {
    "VCC": "12", "R1": "100", "R2": "22", "RC": "2.2",
    "RE": "1.0", "beta": "100", "VBE": "0.70",
}

# The form takes resistors in kOhm; the engineering layer works in Ohm.
KOHM_FIELDS = ("R1", "R2", "RC", "RE")

FIELDS = (
    ("VCC", "VCC (Supply Voltage)", "V"),
    ("R1", "R1 (Upper Divider)", "k\u03a9"),
    ("R2", "R2 (Lower Divider)", "k\u03a9"),
    ("RC", "RC (Collector Resistor)", "k\u03a9"),
    ("RE", "RE (Emitter Resistor)", "k\u03a9"),
    ("beta", "\u03b2 (Current Gain)", ""),
    ("VBE", "VBE (Base-Emitter Voltage)", "V"),
)


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

    app.jinja_env.filters["ma"] = lambda amps: f"{amps * 1000:.2f}"
    app.jinja_env.filters["ma3"] = lambda amps: f"{amps * 1000:.3f}"
    app.jinja_env.filters["ua"] = lambda amps: f"{amps * 1e6:.1f}"
    app.jinja_env.filters["volts"] = lambda v: f"{v:.2f}"
    app.jinja_env.filters["volts3"] = lambda v: f"{v:.3f}"
    app.jinja_env.filters["pct"] = (
        lambda p: "\u2014" if p is None else f"{p:.2f}")

    @app.get("/")
    def index():
        return render_template("index.html", fields=FIELDS, values=DEFAULTS,
                               errors=[], result=None, vce_sat=VCE_SAT)

    @app.post("/calculate")
    def calculate():
        inputs, errors = parse_inputs(to_ohms(request.form))
        if errors:
            return render_template("index.html", fields=FIELDS,
                                   values=request.form, errors=errors,
                                   result=None, vce_sat=VCE_SAT)

        exact = solve_exact(**vars(inputs))
        approx = solve_approximate(**vars(inputs))
        cmp = compare(exact, approx, inputs.beta, inputs.RE, inputs.R2)
        return render_template("index.html", fields=FIELDS,
                               values=request.form, errors=[],
                               result={"exact": exact, "cmp": cmp},
                               vce_sat=VCE_SAT)

    return app


app = create_app()
