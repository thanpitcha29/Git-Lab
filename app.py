"""Flask entry point: routes only, engineering lives in bias/."""

from flask import Flask, render_template, request

from bias.calculator import compare, solve_approximate, solve_exact
from bias.validation import parse_inputs

DEFAULTS = {
    "VCC": "12", "R1": "47000", "R2": "10000", "RC": "2200",
    "RE": "1000", "beta": "150", "VBE": "0.7",
}

FIELDS = (
    ("VCC", "VCC supply", "V"),
    ("R1", "R1 (upper divider)", "\u03a9"),
    ("R2", "R2 (lower divider)", "\u03a9"),
    ("RC", "RC (collector)", "\u03a9"),
    ("RE", "RE (emitter)", "\u03a9"),
    ("beta", "beta (hFE)", ""),
    ("VBE", "VBE (base-emitter)", "V"),
)


def create_app() -> Flask:
    app = Flask(__name__)

    app.jinja_env.filters["ma"] = lambda amps: f"{amps * 1000:.3f}"
    app.jinja_env.filters["ua"] = lambda amps: f"{amps * 1e6:.3f}"
    app.jinja_env.filters["volts"] = lambda v: f"{v:.3f}"
    app.jinja_env.filters["pct"] = (
        lambda p: "\u2014" if p is None else f"{p:.2f}")

    @app.get("/")
    def index():
        return render_template("index.html", fields=FIELDS, values=DEFAULTS,
                               errors=[], result=None)

    @app.post("/calculate")
    def calculate():
        inputs, errors = parse_inputs(request.form)
        if errors:
            return render_template("index.html", fields=FIELDS,
                                   values=request.form, errors=errors,
                                   result=None)

        exact = solve_exact(**vars(inputs))
        approx = solve_approximate(**vars(inputs))
        cmp = compare(exact, approx, inputs.beta, inputs.RE, inputs.R2)
        return render_template("index.html", fields=FIELDS,
                               values=request.form, errors=[],
                               result={"exact": exact, "cmp": cmp})

    return app


app = create_app()
