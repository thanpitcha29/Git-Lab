import unittest

from app import create_app

# Resistors are entered in kOhm, matching the form labels.
VALID = {"VCC": "12", "R1": "47", "R2": "10", "RC": "2.2",
         "RE": "1", "beta": "150", "VBE": "0.7"}


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_index_shows_form(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'name="VCC"', r.data)
        self.assertIn(b'name="RE"', r.data)
        self.assertIn(b"Lab 02", r.data)

    def test_post_computes_and_renders(self):
        r = self.client.post("/calculate", data=VALID)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"7.76", r.data)                       # VCE in the result card
        self.assertIn(b"1.32", r.data)                       # IC in the result card
        self.assertIn(b"Active region approximation OK", r.data)

    def test_kohm_input_is_scaled_to_ohms(self):
        r = self.client.post("/calculate", data=VALID)
        self.assertIn(b"1.324", r.data)       # 47 kOhm -> 1.324 mA exact
        # 47000 kOhm is 47 MOhm: the divider collapses and the device is off.
        r2 = self.client.post("/calculate", data={**VALID, "R1": "47000"})
        self.assertIn(b"Cutoff", r2.data)

    def test_post_rejects_bad_input_without_crashing(self):
        r = self.client.post("/calculate", data={**VALID, "R1": "abc"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"R1 must be a number", r.data)
        self.assertNotIn(b"Traceback", r.data)

    def test_approximate_saturation_is_explained(self):
        r = self.client.post("/calculate", data={**VALID, "RC": "7.5"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"in saturation by itself", r.data)


if __name__ == "__main__":
    unittest.main()
