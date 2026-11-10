import unittest

from app import create_app

VALID = {"VCC": "12", "R1": "47000", "R2": "10000", "RC": "2200",
         "RE": "1000", "beta": "150", "VBE": "0.7"}


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_index_shows_form(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'name="VCC"', r.data)
        self.assertIn(b'name="RE"', r.data)

    def test_post_computes_and_renders(self):
        r = self.client.post("/calculate", data=VALID)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"1.324", r.data)      # IC in mA
        self.assertIn(b"7.755", r.data)      # VCE in V
        self.assertIn(b"Active", r.data)

    def test_post_rejects_bad_input_without_crashing(self):
        r = self.client.post("/calculate", data={**VALID, "R1": "abc"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"R1 must be a number", r.data)
        self.assertNotIn(b"Traceback", r.data)


if __name__ == "__main__":
    unittest.main()
