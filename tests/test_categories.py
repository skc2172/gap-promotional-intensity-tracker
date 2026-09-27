"""Category routing and saved-evidence regression tests; no network required."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gap_tracker.categories import CATEGORIES, category_config
from gap_tracker.collect import collect
from gap_tracker.parse import normalize, parse
from gap_tracker.metrics import calculate


class CategoryTests(unittest.TestCase):
    def payload(self, cid):
        return {"pagination": {"currentPage": "0", "pageNumberTotal": "1"}, "locale": "en_US", "categories": [{"categoryId": cid, "ccList": [
            {"styleId": "s1", "ccId": "c1"}]}], "products": [{"styleId": "s1",
            "styleName": "Test", "styleColors": [{"ccId": "c1", "regularPrice": "100",
            "effectivePrice": "70", "percentageOff": 0, "priceType": "P"}]}]}

    def response(self, body):
        r = Mock(content=body, text=body.decode(), status_code=200, headers={})
        r.request.headers = {}
        r.url = "https://example.test/response"
        r.json.side_effect = lambda: json.loads(body)
        return r

    def test_all_categories_route_and_round_trip(self):
        for key in CATEGORIES:
            with self.subTest(category=key), tempfile.TemporaryDirectory() as tmp:
                config = category_config(key)
                payload = self.payload(config['category_id'])
                html = b'plp-product-list plp-category-products-endpoint\\":true'
                with patch('gap_tracker.collect.requests.get', side_effect=[
                    self.response(html), self.response(json.dumps(payload).encode())]) as get:
                    with contextlib.redirect_stdout(io.StringIO()):
                        raw = collect(Path(tmp) / 'raw', key)
                        rows = parse(raw, Path(tmp) / 'processed')
                self.assertEqual(get.call_args_list[1].kwargs['params']['cid'], config['category_id'])
                self.assertEqual(get.call_args_list[1].kwargs['params']['department'], config['department_id'])
                self.assertEqual(rows[0]['category'], config['category'])
                self.assertEqual(rows[0]['source_percentage_off'], 0)
                self.assertEqual(rows[0]['source_price_type'], 'P')
                self.assertEqual(calculate(rows)['share_discounted_at_least_30_pct'], 1)
                self.assertEqual((raw / 'page.html').read_bytes(), html)
                (raw / 'products.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    parse(raw, Path(tmp) / 'processed')

    def test_wrong_category_rejected(self):
        config = category_config('men-jeans')
        config['requests'] = [{'file': 'products.json', 'collected_at': '2026-09-25T12:00:00+00:00'}]
        with self.assertRaisesRegex(ValueError, 'Unexpected category'):
            normalize(self.payload('5664'), config)

    def test_conflicting_manifest_rejected(self):
        config = category_config('men-jeans')
        config['category_id'] = '5664'
        config['requests'] = [{'file': 'products.json', 'collected_at': '2026-09-25T12:00:00+00:00'}]
        with self.assertRaisesRegex(ValueError, 'conflicting category'):
            normalize(self.payload('5664'), config)

    def test_block_saved_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = self.response(b'Access denied')
            response.status_code = 403
            response.raise_for_status.side_effect = RuntimeError('403')
            with patch('gap_tracker.collect.requests.get', return_value=response) as get:
                with self.assertRaises(RuntimeError), contextlib.redirect_stdout(io.StringIO()):
                    collect(Path(tmp), 'men-tshirts')
            self.assertEqual(get.call_count, 1)
            folder = next(Path(tmp).iterdir())
            self.assertEqual((folder / 'page.html').read_bytes(), b'Access denied')
            self.assertEqual(json.loads((folder / 'manifest.json').read_text())['status'], 'incomplete')


class BatchTests(unittest.TestCase):
    def test_resume_does_not_recollect_saved_response(self):
        from gap_tracker.current import run
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / 'batch.json'
            batch.write_text(json.dumps({'categories': {'men-jeans': {
                'raw_snapshot': 'data/raw/saved-men-jeans', 'status': 'failed'}}}))
            with patch('gap_tracker.current.collect') as collect_mock, \
                 patch('gap_tracker.current.parse') as parse_mock, \
                 patch('gap_tracker.current.write_metrics'):
                state = run(batch, ['men-jeans'])
            collect_mock.assert_not_called()
            parse_mock.assert_called_once_with(Path('data/raw/saved-men-jeans'))
            self.assertEqual(state['categories']['men-jeans']['status'], 'complete')
