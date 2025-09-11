import unittest
from src.detectors import detect

ETF_ROW = {"ETF":"Y", "Test Issue":"N"}
ETN_ROW = {"ETF":"N", "Test Issue":"N"}

class TestBrandAndDuration(unittest.TestCase):
    # False positives that should be excluded (duration/cash/muni)
    def test_duration_ultra_short_muni_excluded(self):
        m, _, _, _ = detect("Allspring Ultra Short Municipal ETF", ETF_ROW)
        self.assertFalse(m)

    def test_duration_ultra_short_government_excluded(self):
        m, _, _, _ = detect("PIMCO Ultra Short Government Active ETF", ETF_ROW)
        self.assertFalse(m)

    def test_duration_ultra_short_muni_goldman_excluded(self):
        m, _, _, _ = detect("Goldman Sachs Ultra Short Municipal Income ETF", ETF_ROW)
        self.assertFalse(m)

    def test_duration_ultra_short_muni_jpm_excluded(self):
        m, _, _, _ = detect("JPMorgan Ultra-Short Municipal Income ETF", ETF_ROW)
        self.assertFalse(m)

    # Missed positives previously: brand implies leverage even without '2x/3x' tokens
    def test_ultrapro_implies_3x(self):
        m, cat, reasons, etp_type = detect("ProShares UltraPro QQQ", ETF_ROW)
        self.assertTrue(m)
        self.assertIn("brand_ultrapro_implies_3x", reasons)
        self.assertIn(cat, ("leveraged_index_long","leveraged_single_stock_long"))

    def test_ultra_implies_2x_long(self):
        m, cat, reasons, etp_type = detect("ProShares Ultra Silver", ETF_ROW)
        self.assertTrue(m)
        self.assertIn("brand_proshares_ultra_implies_2x", reasons)

    def test_ultrashort_implies_minus2x(self):
        m, cat, reasons, etp_type = detect("ProShares UltraShort Dow30", ETF_ROW)
        self.assertTrue(m)
        self.assertIn("brand_proshares_ultrashort_implies_minus2x", reasons)
        self.assertIn("leveraged_index_inverse", cat)

    # Keep Goldman 'gold' exclusion (but still allow true commodity contexts)
    def test_goldman_not_commodity(self):
        m, _, _, _ = detect("Goldman Sachs ActiveBeta U.S. Large Cap Equity ETF", ETF_ROW)
        self.assertFalse(m)

if __name__ == "__main__":
    unittest.main(verbosity=2)
