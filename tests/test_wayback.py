"""Synthetic contract cases; no test records are emitted as research data."""
import json
import unittest
from copy import deepcopy

from gap_tracker.parse import FIELDS
from gap_tracker.parse_wayback import inspect_html, normalize_archived_api
from gap_tracker.wayback import confirmed_timestamp, ranked_candidates, same_category, same_category_api

BREADCRUMB = '<script type="application/ld+json">' + json.dumps({
    '@type': 'BreadcrumbList', 'itemListElement': [{'name': 'Women'},
    {'name': 'Jeans', '@id': 'https://www.gap.com/browse/category.do?cid=5664'}]}) + '</script>'


class ArchivedHtmlTests(unittest.TestCase):
    def test_shell_is_not_zero_stock_or_full_price(self):
        html = BREADCRUMB + '<div id="plp-product-card-skeleton">0 of 0 items</div>'
        report = inspect_html(html)
        self.assertEqual(report['inspection_status'], 'category_shell_no_product_data')
        self.assertEqual(report['structure']['product_skeletons'], 1)
        self.assertEqual(report['observations'], [])
        self.assertIsNone(report['missing_price_rate'])
        self.assertFalse(report['metrics_eligible'])

    def test_page_offer_is_not_a_product_discount(self):
        report = inspect_html(BREADCRUMB + '<header><p>Extra 40% off at checkout</p></header>')
        self.assertEqual(report['page_promo_evidence'][0]['scope'], 'page_header')
        self.assertEqual(report['product_observations_extracted'], 0)

    def test_wrong_category_rejected(self):
        self.assertEqual(inspect_html('<title>Access denied</title>')['inspection_status'],
                         'wrong_or_unverified_category')

    def test_unrecognized_product_data_requires_inspection(self):
        html = BREADCRUMB + '<script type="application/ld+json">{"@type":"Product","name":"Test"}</script>'
        self.assertEqual(inspect_html(html)['inspection_status'], 'unrecognized_product_structure')

    def test_next_template_price_labels_are_not_observations(self):
        flight = [1, '{"regularPrice":"{{regularPrice}}","currentPrice":"{{currentPrice}}"}']
        report = inspect_html(BREADCRUMB + '<script>self.__next_f.push(' + json.dumps(flight) + ')</script>')
        self.assertEqual(report['structure']['numeric_price_fields'], 0)
        self.assertEqual(report['structure']['next_flight_chunks'], 1)


class ArchiveSelectionTests(unittest.TestCase):
    def test_filters_and_malformed_category_ids_rejected(self):
        base = 'https://www.gap.com/browse/women/jeans?cid=5664'
        self.assertTrue(same_category(base + '&bc=true'))
        for suffix in ['&style=123', '&color=blue', '%5C', '&department=75', '&cid=75']:
            self.assertFalse(same_category(base + suffix))

    def test_nearest_is_absolute_time_not_first_index_row(self):
        header = ['timestamp', 'original', 'statuscode', 'mimetype']
        url = 'https://www.gap.com/browse/women/jeans?cid=5664'
        index = [header, ['20250301000000', url, '200', 'text/html'],
                 ['20250315130000', url, '200', 'text/html'],
                 ['20250315120000', url+'&style=1', '200', 'text/html']]
        self.assertEqual(ranked_candidates(index, '2025-03')[0]['timestamp'], '20250315130000')

    def test_timestamp_is_confirmed_and_redirects_not_followed(self):
        meta = {'status_code': 200, 'headers': {'Memento-Datetime': 'Fri, 11 Apr 2025 13:25:36 GMT'}}
        self.assertEqual(confirmed_timestamp(meta, '20250411132536'), '20250411132536')
        self.assertIsNone(confirmed_timestamp(meta, '20250315120000'))
        meta['status_code'] = 302
        self.assertIsNone(confirmed_timestamp(meta, '20250411132536'))

    def test_filtered_api_capture_not_category_alternative(self):
        url = 'https://api.gap.com/commerce/search/products/v2/cc?brand=gap&market=us&cid=5664&locale=en_US&pageNumber=0&department=136'
        self.assertTrue(same_category_api(url))
        self.assertFalse(same_category_api(url+'&style=1113004'))


class ArchivedApiTests(unittest.TestCase):
    def setUp(self):
        self.attempt = {'actual_archive_timestamp': '20250411132536', 'retrieved_at': '2026-09-25T21:00:00Z',
                        'candidate': {'original': 'https://api.gap.com/commerce/search/products/v2/cc?cid=5664'},
                        'archive_url': 'https://web.archive.org/web/20250411132536id_/example',
                        'raw_file': 'products.json', 'sha256': 'test'}
        self.color = {'ccId': 'c1', 'regularPrice': '100', 'effectivePrice': '70', 'priceType': 'P',
                      'percentageOff': '30', 'ccLevelMarketingFlags': [{'content': 'Extra 40% at checkout'}],
                      'ccMarketingFlagsDetails': [{'name': 'Extra 40% at checkout', 'position': '3'}]}
        self.payload = {'locale': 'en_US', 'categories': [{'categoryId': '5664', 'ccList': [{'styleId': 's1', 'ccId': 'c1'}]}],
                        'products': [{'styleId': 's1', 'styleName': 'Test', 'styleMarketingFlagsDetails': [],
                                      'styleColors': [self.color]}]}

    def normalize(self):
        return normalize_archived_api(self.payload, self.attempt, '2025-03')

    def test_actual_date_and_evidence_preserved(self):
        row = self.normalize()[0]
        self.assertEqual(set(row), set(FIELDS))
        self.assertEqual(row['snapshot_date'], '2025-04-11')
        self.assertEqual(row['provenance']['requested_target_period'], '2025-03')
        self.assertEqual(row['discount_pct'], '30.0000')
        self.assertEqual(row['source_price_type'], 'P')
        self.assertEqual(row['promo_evidence']['ccMarketingFlagsDetails'], self.color['ccMarketingFlagsDetails'])
        self.assertIsNone(row['price_basis'])  # Arithmetic alone does not establish display semantics.

    def test_missing_price_and_offer_not_imputed(self):
        self.color.pop('regularPrice')
        self.color.pop('ccLevelMarketingFlags')
        row = self.normalize()[0]
        self.assertIsNone(row['original_price'])
        self.assertIsNone(row['discount_pct'])
        self.assertIsNone(row['is_discounted'])
        self.assertIsNone(row['promo_text'])

    def test_unlisted_colors_excluded(self):
        extra = deepcopy(self.color)
        extra['ccId'] = 'unlisted'
        self.payload['products'][0]['styleColors'].append(extra)
        self.assertEqual(len(self.normalize()), 1)

    def test_missing_join_or_timestamp_rejected(self):
        self.attempt['actual_archive_timestamp'] = None
        with self.assertRaises(ValueError):
            self.normalize()
        self.attempt['actual_archive_timestamp'] = '20250411132536'
        self.payload['products'] = []
        with self.assertRaises(ValueError):
            self.normalize()

    def test_duplicate_and_invalid_prices_rejected(self):
        self.payload['products'][0]['styleColors'].append(deepcopy(self.color))
        with self.assertRaises(ValueError):
            self.normalize()
        self.payload['products'][0]['styleColors'].pop()
        self.color['effectivePrice'] = '101'
        with self.assertRaises(ValueError):
            self.normalize()

class PriceBasisReviewTests(unittest.TestCase):
    def test_review_requires_matching_capture_and_unchanged_evidence(self):
        import tempfile
        import hashlib
        from pathlib import Path
        from gap_tracker.parse_wayback import reviewed_basis
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder) / 'bundle.js'
            evidence.write_bytes(b'example reviewed evidence')
            review = Path(folder) / 'review.json'
            review.write_text(json.dumps({'archive_timestamp': '20250411132536',
                'price_basis': 'displayed_current_vs_retailer_reference',
                'evidence': [{'file': str(evidence), 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}]}))
            attempt = {'actual_archive_timestamp': '20250411132536'}
            self.assertEqual(reviewed_basis(review, attempt), 'displayed_current_vs_retailer_reference')
            self.assertIsNone(reviewed_basis(review, {'actual_archive_timestamp': '20260301000000'}))
            evidence.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                reviewed_basis(review, attempt)
