import unittest

from bias.calculator import solve_exact

DEFAULTS = dict(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=2_200.0,
                RE=1_000.0, beta=150.0, VBE=0.7)


class ExactSolverTest(unittest.TestCase):
    def test_active_case(self):
        op = solve_exact(**DEFAULTS)
        self.assertEqual(op.region, "active")
        self.assertAlmostEqual(op.IB, 8.824501487e-06, places=9)
        self.assertAlmostEqual(op.IC, 1.323675223e-03, places=9)
        self.assertAlmostEqual(op.IE, 1.332499725e-03, places=9)
        self.assertAlmostEqual(op.VE, 1.3324997246, places=6)
        self.assertAlmostEqual(op.VB, 2.0324997246, places=6)
        self.assertAlmostEqual(op.VC, 9.0879145092, places=6)
        self.assertAlmostEqual(op.VCE, 7.7554147846, places=6)

    def test_cutoff_when_divider_below_vbe(self):
        op = solve_exact(VCC=12.0, R1=100_000.0, R2=5_000.0, RC=2_200.0,
                         RE=1_000.0, beta=150.0, VBE=0.7)
        self.assertEqual(op.region, "cutoff")
        self.assertEqual((op.IB, op.IC, op.IE, op.VE), (0.0, 0.0, 0.0, 0.0))
        self.assertAlmostEqual(op.VB, 0.5714285714, places=6)
        self.assertAlmostEqual(op.VC, 12.0, places=9)
        self.assertAlmostEqual(op.VCE, 12.0, places=9)

    def test_saturation_when_vce_below_threshold(self):
        op = solve_exact(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=10_000.0,
                         RE=1_000.0, beta=150.0, VBE=0.7)
        self.assertEqual(op.region, "saturation")
        self.assertLess(op.VCE, 0.2)
        self.assertAlmostEqual(op.IC_sat, 11.8 / 11_000.0, places=9)


if __name__ == "__main__":
    unittest.main()
