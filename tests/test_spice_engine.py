import unittest
from pathlib import Path

import charts
import spice_engine


def form(**overrides):
    data = dict(spice_engine.SIM_DEFAULTS)
    data.update(overrides)
    return data


class NetlistTest(unittest.TestCase):
    def test_defaults_convert_to_ohms_and_farads_once(self):
        params, errors = spice_engine.parse_params(form(RE="2"))
        self.assertEqual(errors, [])
        self.assertAlmostEqual(params["RE"], 2000.0)
        self.assertAlmostEqual(params["CIN"], 10e-6)
        self.assertAlmostEqual(params["amp"], 0.010)

    def test_each_analysis_gets_its_own_directive(self):
        params, _ = spice_engine.parse_params(form())
        self.assertIn(".op", spice_engine.build_netlist(params, "dc"))
        self.assertIn(".ac dec 20", spice_engine.build_netlist(params, "ac"))
        self.assertIn(".tran", spice_engine.build_netlist(params, "tran"))

    def test_netlist_uses_converted_value_not_the_typed_one(self):
        params, _ = spice_engine.parse_params(form(RE="2"))
        netlist = spice_engine.build_netlist(params, "dc")
        self.assertIn("RE emit 0 2000", netlist)
        self.assertNotIn("RE emit 0 2\n", netlist)

    def test_netlist_has_the_reference_circuit(self):
        params, _ = spice_engine.parse_params(form())
        netlist = spice_engine.build_netlist(params, "tran")
        for piece in ("R1 vcc base", "R2 base 0", "RC vcc coll",
                      "RE emit 0", "CIN src base", "COUT coll out",
                      "RL out 0", "Q1 coll base emit Q2N3904",
                      "sin(0"):
            self.assertIn(piece, netlist)

    def test_unknown_analysis_is_refused(self):
        params, _ = spice_engine.parse_params(form())
        with self.assertRaises(spice_engine.SpiceError):
            spice_engine.build_netlist(params, "fft")


class ParamValidationTest(unittest.TestCase):
    def test_zero_emitter_resistor_is_an_input_error(self):
        params, errors = spice_engine.parse_params(form(RE="0"))
        self.assertIsNone(params)
        self.assertIn("RE must be greater than 0 \u03a9", errors)

    def test_text_is_an_input_error(self):
        params, errors = spice_engine.parse_params(form(R1="abc"))
        self.assertIsNone(params)
        self.assertIn("R1 must be a number", errors)

    def test_missing_field_is_reported(self):
        data = form()
        del data["RL"]
        params, errors = spice_engine.parse_params(data)
        self.assertIsNone(params)
        self.assertIn("RL must be a number", errors)

    def test_frequency_outside_range_is_refused(self):
        params, errors = spice_engine.parse_params(form(freq_hz="0.01"))
        self.assertIsNone(params)
        self.assertIn("Frequency must be between 1 Hz and 10 MHz", errors)


class ParseTest(unittest.TestCase):
    def test_wrdata_rows_keep_each_vector_apart(self):
        path = Path(spice_engine.RUNS_DIR) / "_unit_wrdata.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(" 1 2 3 4\n 5 6 7 8\n", encoding="ascii")
        try:
            rows = spice_engine.parse_wrdata(path)
        finally:
            path.unlink()
        self.assertEqual(rows, [
            [(1.0, 2.0), (3.0, 4.0)],
            [(5.0, 6.0), (7.0, 8.0)],
        ])

    def test_empty_file_raises_instead_of_returning_junk(self):
        path = Path(spice_engine.RUNS_DIR) / "_unit_empty.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="ascii")
        try:
            with self.assertRaises(spice_engine.SpiceError):
                spice_engine.parse_wrdata(path)
        finally:
            path.unlink()


class PhaseTest(unittest.TestCase):
    def test_wrapped_phase_is_unwrapped_continuously(self):
        # ngspice vp() wraps at +/-pi; the curve must not jump.
        values = [-170.0, -179.0, 179.0, 170.0, 90.0]
        out = spice_engine._unwrap_degrees(values)
        self.assertEqual(out, [-170.0, -179.0, -181.0, -190.0, -270.0])

    def test_ac_phase_is_in_degrees_not_radians(self):
        info = spice_engine.engine_info()
        if not info["available"]:
            self.skipTest("ngspice is not installed on this machine")
        params, _ = spice_engine.parse_params(form())
        ac = spice_engine.run_analysis("ac", params)["ac"]
        # Inverting amplifier: midband phase sits near -180 degrees, not -3.14.
        self.assertLess(ac["phase_deg"][len(ac["phase_deg"]) // 2], -150.0)
        self.assertGreater(ac["phase_deg"][len(ac["phase_deg"]) // 2], -210.0)


class ChartTest(unittest.TestCase):
    def test_chart_has_axes_and_series(self):
        svg = charts.line_chart(
            [{"label": "gain", "x": [10, 100, 1000], "y": [-20, -6, -3]}],
            x_label="Frequency (Hz)", y_label="Gain (dB)", x_log=True)
        self.assertIn("<svg", svg)
        self.assertIn("polyline", svg)
        self.assertIn("Frequency (Hz)", svg)

    def test_labels_are_escaped(self):
        svg = charts.line_chart(
            [{"label": "<script>", "x": [0, 1], "y": [0, 1]}],
            x_label="t", y_label="v")
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)

    def test_empty_series_is_explained(self):
        self.assertIn("No data", charts.line_chart([], x_label="t", y_label="v"))


class EngineTest(unittest.TestCase):
    def test_engine_reports_its_version(self):
        info = spice_engine.engine_info()
        if not info["available"]:
            self.skipTest("ngspice is not installed on this machine")
        self.assertIn("ngspice", info["version"])
        self.assertEqual(info["model"], "2N3904")

    def test_dc_run_returns_real_operating_point(self):
        info = spice_engine.engine_info()
        if not info["available"]:
            self.skipTest("ngspice is not installed on this machine")
        params, _ = spice_engine.parse_params(form())
        result = spice_engine.run_analysis("dc", params)
        dc = result["dc"]
        # 2N3904 card with BF = 416, not the analytical beta = 100.
        self.assertAlmostEqual(dc["vb_v"], 2.0037, places=2)
        self.assertAlmostEqual(dc["ic_ma"], 1.324, places=2)
        self.assertAlmostEqual(dc["vce_v"], 7.754, places=2)
        self.assertEqual(dc["region"], "active")
        self.assertTrue(Path(result["run_dir"], "circuit.cir").is_file())

    def test_ac_run_reports_gain_and_phase(self):
        info = spice_engine.engine_info()
        if not info["available"]:
            self.skipTest("ngspice is not installed on this machine")
        params, _ = spice_engine.parse_params(form())
        result = spice_engine.run_analysis("ac", params)
        ac = result["ac"]
        self.assertGreater(len(ac["freq_hz"]), 50)
        self.assertIsNotNone(ac["gain_db_at_1k"])
        self.assertLess(ac["gain_db_at_1k"], 10.0)
        self.assertGreater(ac["gain_db_at_1k"], 0.0)
        self.assertEqual(len(ac["freq_hz"]), len(ac["phase_deg"]))
        # Low-frequency corner from the 10 uF coupling capacitors is in range.
        self.assertIsNotNone(ac["f_low_hz"])
        self.assertLess(ac["f_low_hz"], 100.0)

    def test_tran_run_returns_two_waveforms(self):
        info = spice_engine.engine_info()
        if not info["available"]:
            self.skipTest("ngspice is not installed on this machine")
        params, _ = spice_engine.parse_params(form())
        result = spice_engine.run_analysis("tran", params)
        tran = result["tran"]
        self.assertGreater(len(tran["time_ms"]), 50)
        self.assertEqual(len(tran["time_ms"]), len(tran["vin_mv"]))
        self.assertEqual(len(tran["time_ms"]), len(tran["vout_mv"]))
        self.assertTrue(tran["inverted"])
        # 10 mV peak in, unbypassed RE: gain near -RC'/(RE+re) ~ 1.76.
        self.assertAlmostEqual(tran["vin_peak_mv"], 10.0, places=1)
        self.assertGreater(tran["gain"], 1.4)
        self.assertLess(tran["gain"], 2.2)


if __name__ == "__main__":
    unittest.main()
