"""Archive selection, category routing and evidence gates; no network calls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from gap_tracker.backfill import eligible
from gap_tracker.backfill_publish import representative, verified_review, BASIS
from gap_tracker.categories import category_config
from gap_tracker.parse_wayback import normalize_archived_api


class BackfillTests(unittest.TestCase):
    def test_unfiltered_category_identity(self):
        url = 'https://api.gap.com/commerce/search/products/v2/cc?brand=gap&market=us&locale=en_US&cid=6998&department=75&pageNumber=0'
        self.assertTrue(eligible(url, 'men-jeans'))
        for suffix in ['&color=black', '&style=123', '&sortByField=price', '&ignoreInventory=true']:
            self.assertFalse(eligible(url+suffix, 'men-jeans'))
        self.assertFalse(eligible(url, 'women-jeans'))
        self.assertFalse(eligible(url.replace('pageNumber=0','pageNumber=1'), 'men-jeans'))

    def test_monthly_selection_uses_coverage_then_sample_not_discount(self):
        def candidate(ts, n, coverage=1):
            return {'timestamp': ts, 'coverage': coverage, 'category_key':'men-jeans',
                    'rows':[{'snapshot_date': ts[:4]+'-'+ts[4:6]+'-'+ts[6:8]}]*n}
        early = candidate('20240101000000',100)
        larger = candidate('20240102000000',120)
        partial = candidate('20240103000000',300,.9)
        next_month = candidate('20240201000000',80)
        result = representative([partial, larger, early, next_month])
        self.assertEqual(result,[larger,next_month])

    def test_review_is_bound_to_capture_url_hash_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'evidence';path.write_bytes(b'archived mapping')
            attempt={'actual_archive_timestamp':'20240101000000','sha256':'bodyhash', 'candidate':{'original':'source'}}
            review={'archive_timestamp':'20240101000000','sha256':'bodyhash','source_url':'source',
                    'price_basis':BASIS,'rationale':'Verified source mapping',
                    'evidence':[{'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}
            self.assertEqual(verified_review(attempt,[review]),review)
            self.assertIsNone(verified_review({**attempt,'sha256':'other'},[review]))
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):verified_review(attempt,[review])

    def test_historical_category_and_actual_capture_date(self):
        payload={'locale':'en_US','categories':[{'categoryId':'6998','ccList':[{'styleId':'s','ccId':'c'}]}],
                 'products':[{'styleId':'s','styleName':'Jeans','styleColors':[{'ccId':'c','regularPrice':'100','effectivePrice':'70'}]}]}
        attempt={'actual_archive_timestamp':'20240210143119','raw_file':'old.json', 'retrieved_at':'2026-09-26',
                 'archive_url':'archive','candidate':{'original':'source'},'sha256':'hash'}
        row=normalize_archived_api(payload,attempt,None,BASIS,category_config('men-jeans'))[0]
        self.assertEqual(row['category'],'Men / Jeans')
        self.assertEqual(row['snapshot_date'],'2024-02-10')
        self.assertEqual(row['discount_pct'],'30.0000')
        self.assertIsNone(row['provenance']['requested_target_period'])


class ArchiveTransportTests(unittest.TestCase):
    def test_access_denial_never_uses_fallback(self):
        from unittest.mock import patch
        from gap_tracker.archive_http import fetch
        with tempfile.TemporaryDirectory() as tmp:
            with patch('gap_tracker.archive_http.requests_fetch', return_value={'status_code':403}), \
                 patch('gap_tracker.archive_http.subprocess.run') as fallback:
                self.assertEqual(fetch('https://web.archive.org/x',Path(tmp)/'body')['status_code'],403)
                fallback.assert_not_called()
