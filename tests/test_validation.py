import unittest

from bias.validation import parse_inputs

VALID = {"VCC": "12", "R1": "47000", "R2": "10000", "RC": "2200",
         "RE": "1000", "beta": "150", "VBE": "0.7"}


class ValidationTest(unittest.TestCase):
    def test_valid_form(self):
        inputs, errors = parse_inputs(VALID)
        self.assertEqual(errors, [])
        self.assertAlmostEqual(inputs.R1, 47000.0)
        self.assertAlmostEqual(inputs.VBE, 0.7)

    def test_missing_field_gives_message_not_keyerror(self):
        form = {k: v for k, v in VALID.items() if k != "R2"}
        inputs, errors = parse_inputs(form)
        self.assertIsNone(inputs)
        self.assertTrue(any("R2" in e for e in errors))

    def test_non_numeric_text(self):
        inputs, errors = parse_inputs({**VALID, "R1": "47k"})
        self.assertIsNone(inputs)
        self.assertTrue(any("R1" in e and "number" in e for e in errors))

    def test_non_positive_resistance_and_beta(self):
        inputs, errors = parse_inputs({**VALID, "RC": "0", "RE": "0", "beta": "0"})
        self.assertIsNone(inputs)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("RE" in e for e in errors))
        self.assertTrue(any("beta" in e for e in errors))

    def test_zero_collector_resistor_is_legal(self):
        inputs, errors = parse_inputs({**VALID, "RC": "0"})
        self.assertEqual(errors, [])
        self.assertEqual(inputs.RC, 0.0)


if __name__ == "__main__":
    unittest.main()
