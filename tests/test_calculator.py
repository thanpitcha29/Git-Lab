import unittest

from bias.calculator import solve_exact, solve_approximate, compare

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

    def test_approximate_matches_exact_on_stiff_divider(self):
        kwargs = dict(DEFAULTS, beta=300.0)
        exact = solve_exact(**kwargs)
        approx = solve_approximate(**kwargs)
        self.assertLess(abs(approx.IC - exact.IC) / abs(exact.IC) * 100, 5.0)

    def test_comparison_reports_rule_and_delta(self):
        exact = solve_exact(**DEFAULTS)
        approx = solve_approximate(**DEFAULTS)
        cmp = compare(exact, approx, beta=150.0, RE=1_000.0, R2=10_000.0)
        self.assertTrue(cmp.rule_satisfied)
        self.assertAlmostEqual(cmp.beta_re_over_r2, 15.0)
        self.assertAlmostEqual(cmp.delta_ic_pct, 6.16374, places=3)
        self.assertTrue(cmp.approximation_valid)

    def test_approximation_never_valid_outside_active_region(self):
        sat = dict(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=10_000.0,
                   RE=1_000.0, beta=150.0, VBE=0.7)
        cut = dict(VCC=12.0, R1=100_000.0, R2=5_000.0, RC=2_200.0,
                   RE=1_000.0, beta=150.0, VBE=0.7)
        for kwargs in (sat, cut):
            exact = solve_exact(**kwargs)
            approx = solve_approximate(**kwargs)
            cmp = compare(exact, approx, beta=150.0,
                          RE=kwargs["RE"], R2=kwargs["R2"])
            self.assertFalse(cmp.approximation_valid)

    def test_reason_when_only_approximate_route_saturates(self):
        kwargs = dict(VCC=12.0, R1=47_000.0, R2=10_000.0, RC=7_500.0,
                      RE=1_000.0, beta=150.0, VBE=0.7)
        exact = solve_exact(**kwargs)
        approx = solve_approximate(**kwargs)
        self.assertEqual(exact.region, "active")
        self.assertEqual(approx.region, "saturation")
        cmp = compare(exact, approx, beta=150.0, RE=1_000.0, R2=10_000.0)
        self.assertFalse(cmp.approximation_valid)
        self.assertEqual(cmp.invalid_reason, "approximate_saturation")


if __name__ == "__main__":
    unittest.main()
