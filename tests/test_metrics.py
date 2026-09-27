import copy
import json
import tempfile
import unittest
from pathlib import Path

from gap_tracker.metrics import BANDS, calculate, markdown, write_metrics


def rows(prices):
    return [dict(snapshot_date='2026-09-25', source='test', source_url='test', category='Jeans',
                 currency='USD', style_id=str(i // 2), product_id=str(i),
                 original_price=original, current_price=current,
                 promo_text='Extra 50% off', discount_pct='99', is_discounted=True)
            for i, (original, current) in enumerate(prices)]


class MetricsTests(unittest.TestCase):
    def test_full_discounted_and_missing(self):
        data = rows([('100', '100'), ('100', '70'), ('100', '50'), (None, '40'), ('100', '')])
        before = copy.deepcopy(data)
        result = calculate(data)
        self.assertEqual(result['total_observations'], 5)
        self.assertEqual(result['unique_styles_observed'], 3)
        self.assertEqual(result['missing_price_observations'], 2)
        self.assertEqual(result['share_discounted'], .4)
        self.assertEqual(result['share_discounted_at_least_30_pct'], .4)
        self.assertEqual(result['median_discount_pct_among_discounted'], 40)
        self.assertEqual(result['mean_discount_pct_among_discounted'], 40)
        self.assertEqual(result['full_price_observations'], 1)
        self.assertEqual(sum(b['count'] for b in result['discount_bands'].values()), 3)
        self.assertEqual(data, before)

    def test_all_band_boundaries_without_prerounding(self):
        current = ['100', '99.9999', '80.0001', '80', '70.0001', '70', '60.0001', '60', '50.0001', '50', '0']
        result = calculate(rows([('100', c) for c in current]))
        self.assertEqual([result['discount_bands'][b]['count'] for b in BANDS], [1, 2, 2, 2, 2, 2])
        self.assertEqual(result['observations_discounted_at_least_30_pct'], 6)
        self.assertEqual(markdown('89.90', '62.93'), 30)

    def test_odd_median_and_mean(self):
        result = calculate(rows([('100', '90'), ('100', '70'), ('100', '20')]))
        self.assertEqual(result['median_discount_pct_among_discounted'], 30)
        self.assertEqual(result['mean_discount_pct_among_discounted'], 40)

    def test_no_discounted_and_all_unknown(self):
        for prices in [[('100', '100')], [(None, '50'), ('100', None)]]:
            result = calculate(rows(prices))
            self.assertEqual(result['share_discounted'], 0)
            self.assertIsNone(result['median_discount_pct_among_discounted'])
            self.assertIsNone(result['mean_discount_pct_among_discounted'])

    def test_invalid_prices(self):
        for pair in [('0', '0'), ('100', '101'), ('-1', '0'), ('NaN', '1'), ('100', 'Infinity')]:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                calculate(rows([pair]))

    def test_empty_duplicate_and_mixed_snapshots_rejected(self):
        with self.assertRaises(ValueError):
            calculate([])
        data = rows([('100', '70')])
        with self.assertRaises(ValueError):
            calculate(data * 2)
        data = rows([('100', '70'), ('100', '80')])
        data[1]['snapshot_date'] = '2026-09-26'
        with self.assertRaises(ValueError):
            calculate(data)

    def test_separate_reproducible_output_and_preserved_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'observations.json'
            original = json.dumps(rows([('100', '70')])).encode()
            source.write_bytes(original)
            output = write_metrics(source)
            first = output.read_bytes()
            write_metrics(source)
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(json.loads(first)['share_discounted_at_least_30_pct'], 1)

class HistoricalMetricsGateTests(unittest.TestCase):
    def test_unverified_historical_basis_is_rejected(self):
        data = rows([('100', '70')])
        data[0]['source'] = 'gap_wayback'
        with self.assertRaisesRegex(ValueError, 'comparability'):
            calculate(data)
        data[0]['price_basis'] = 'displayed_current_vs_retailer_reference'
        self.assertEqual(calculate(data)['share_discounted'], 1)
