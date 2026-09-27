"""Synthetic pagination cases; fixtures are never research observations."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gap_tracker.collect import collect
from gap_tracker.parse import parse
import test_categories


class PaginationTests(unittest.TestCase):
    payload = test_categories.CategoryTests.payload
    response = test_categories.CategoryTests.response

    def pages(self):
        first = self.payload('5664')
        first['pagination']['pageNumberTotal'] = '2'
        first['totalColors'] = '3'
        second = copy.deepcopy(first)
        second['pagination']['currentPage'] = '1'
        extra = copy.deepcopy(second['products'][0]['styleColors'][0])
        extra['ccId'] = 'c2'
        second['products'][0]['styleColors'].append(extra)
        second['categories'][0]['ccList'].append({'styleId': 's1', 'ccId': 'c2'})
        return first, second

    def responses(self, pages):
        return [self.response(b'plp-product-list plp-category-products-endpoint\\":true'),
                *(self.response(json.dumps(p).encode()) for p in pages)]

    def test_collect_deduplicate_and_preserve_page_provenance(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            with patch('gap_tracker.collect.requests.get', side_effect=self.responses(self.pages())) as get:
                raw = collect(Path(tmp) / 'raw')
            self.assertEqual([c.kwargs['params']['pageNumber'] for c in get.call_args_list[1:]], ['0', '1'])
            rows = parse(raw, Path(tmp) / 'processed')
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]['raw_file'], 'products-page-1.json')
            self.assertEqual(rows[0]['provenance']['additional_occurrences'][0]['raw_file'], 'products-page-1.json')
            report = json.loads((Path(tmp) / 'processed' / raw.name / 'validation.json').read_text())
            self.assertEqual(report['duplicates_removed'], 1)
            self.assertEqual(report['api_total_minus_collected'], 1)
            self.assertEqual(report['pages_collected'], 2)

    def test_conflicting_duplicate_fails(self):
        pages = self.pages()
        pages[1]['products'][0]['styleColors'][0]['effectivePrice'] = '60'
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            with patch('gap_tracker.collect.requests.get', side_effect=self.responses(pages)):
                raw = collect(Path(tmp))
            with self.assertRaisesRegex(ValueError, 'Conflicting observations'):
                parse(raw, Path(tmp) / 'processed')

    def test_repeated_page_or_changed_page_count_is_incomplete(self):
        for field, value in [('currentPage', '0'), ('pageNumberTotal', '3')]:
            pages = self.pages()
            pages[1]['pagination'][field] = value
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
                with patch('gap_tracker.collect.requests.get', side_effect=self.responses(pages)):
                    with self.assertRaises(ValueError):
                        collect(Path(tmp))
                raw = next(Path(tmp).iterdir())
                self.assertTrue((raw / 'products-page-1.json').exists())
                self.assertEqual(json.loads((raw / 'manifest.json').read_text())['status'], 'incomplete')

    def test_later_page_http_failure_preserved_without_retry(self):
        responses = self.responses(self.pages())
        responses[-1] = self.response(b'Access denied')
        responses[-1].status_code = 403
        responses[-1].raise_for_status.side_effect = RuntimeError('403')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            with patch('gap_tracker.collect.requests.get', side_effect=responses) as get:
                with self.assertRaises(RuntimeError):
                    collect(Path(tmp))
            self.assertEqual(get.call_count, 3)
            raw = next(Path(tmp).iterdir())
            self.assertEqual((raw / 'products-page-1.json').read_bytes(), b'Access denied')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                parse(raw)
