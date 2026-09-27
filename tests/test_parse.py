"""Small synthetic unit cases, never used as research observations."""
import copy
import unittest

from gap_tracker.parse import normalize, price


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"category": "Women / Jeans", "source_url": "https://www.gap.com/browse/women/jeans?cid=5664",
                         "requests": [{"file": "products.json", "collected_at": "2026-09-25T15:00:00+00:00"}]}
        self.color = {"ccId": "color1", "regularPrice": "100", "effectivePrice": "70",
                      "ccLevelMarketingFlags": [{"content": "Extra 50% at checkout"}]}
        self.payload = {"locale": "en_US", "categories": [{"categoryId": "5664", "ccList": [
            {"styleId": "style1", "ccId": "color1"}]}], "products": [{"styleId": "style1",
            "styleName": "Test product", "styleColors": [self.color]}]}

    def row(self):
        return normalize(self.payload, self.manifest)[0]

    def test_discount_does_not_apply_offer_text(self):
        self.assertEqual(self.row()["discount_pct"], "30.0000")
        self.assertEqual(self.row()["current_price"], "70")
        self.assertTrue(self.row()["is_discounted"])

    def test_missing_original_is_unknown(self):
        del self.color["regularPrice"]
        self.assertIsNone(self.row()["discount_pct"])
        self.assertIsNone(self.row()["is_discounted"])
        self.assertIsNone(self.row()["original_price"])

    def test_missing_current_is_unknown(self):
        del self.color["effectivePrice"]
        self.assertIsNone(self.row()["current_price"])
        self.assertIsNone(self.row()["is_discounted"])

    def test_equal_prices_are_not_discounted(self):
        self.color["effectivePrice"] = "100"
        self.assertFalse(self.row()["is_discounted"])
        self.assertEqual(self.row()["discount_pct"], "0.0000")

    def test_unlisted_swatches_excluded_and_category_duplicates_deduplicated(self):
        extra = copy.deepcopy(self.color)
        extra["ccId"] = "unlisted"
        self.payload["products"][0]["styleColors"].append(extra)
        self.payload["categories"] *= 2
        self.assertEqual(len(normalize(self.payload, self.manifest)), 1)

    def test_missing_flag_is_not_no_promotion(self):
        self.color["ccLevelMarketingFlags"] = []
        self.assertIsNone(self.row()["promo_text"])

    def test_missing_reference_record_fails(self):
        self.payload["products"] = []
        with self.assertRaises(ValueError):
            self.row()

    def test_invalid_prices_fail(self):
        for value in ["NaN", "Infinity", "-1", "70-100", "unknown"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                price(value)

    def test_inverted_prices_fail(self):
        self.color["effectivePrice"] = "110"
        with self.assertRaises(ValueError):
            self.row()

class EvidencePreservationTests(unittest.TestCase):
    setUp = NormalizationTests.setUp
    row = NormalizationTests.row

    def test_raw_fields_preserved_without_interpretation(self):
        self.color.update(percentageOff='30', priceType='P', ccLevelBadges=[{'content': 'New'}])
        self.payload['products'][0]['excludedFromPromotion'] = 'false'
        row = self.row()
        self.assertEqual(row['source_percentage_off'], '30')
        self.assertEqual(row['source_price_type'], 'P')
        self.assertEqual(row['promo_evidence']['style_excluded_from_promotion'], 'false')
        self.assertEqual(row['promo_evidence']['product_color_flags'], self.color['ccLevelMarketingFlags'])
        self.assertEqual(row['price_basis'], 'displayed_current_vs_retailer_reference')
        self.assertIsNone(row['provenance']['archive_timestamp'])

    def test_absent_source_evidence_is_nullable(self):
        row = self.row()
        self.assertIsNone(row['source_percentage_off'])
        self.assertIsNone(row['source_price_type'])
        self.assertIsNone(row['promo_evidence']['style_flags'])


if __name__ == "__main__":
    unittest.main()
