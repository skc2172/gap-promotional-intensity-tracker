"""Read-only dashboard and explicit refresh tests; collection is mocked."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gap_tracker.dashboard_data import ROOT, evidence_rows, load_snapshots, refresh_current


class DashboardDataTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / "data/processed/wayback/2025-03/metrics.json").exists(), "Local research data not bundled")
    def test_saved_snapshots_and_colors(self):
        snapshots, errors = load_snapshots()
        self.assertFalse(errors)
        self.assertTrue(snapshots)
        self.assertFalse(any('schema-v1' in s['id'] for s in snapshots))
        self.assertTrue({'First page only', 'All reported pages', 'Archive alternative'} <= {s['scope'] for s in snapshots})
        latest = snapshots[-1]
        rows = evidence_rows(latest)
        self.assertEqual(len(rows), latest['metrics']['total_observations'])
        self.assertTrue(any(r['Color'] for r in rows))
        archive = next(s for s in snapshots if s['scope'] == 'Archive alternative')
        self.assertEqual(archive['metrics']['snapshot_date'], '2025-04-11')

    def test_bad_metrics_hash_is_not_displayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'data/processed/example'
            folder.mkdir(parents=True)
            (folder / 'metrics.json').write_text(json.dumps({'input': {'sha256': 'wrong'}}))
            (folder / 'observations.json').write_text('[]')
            snapshots, errors = load_snapshots(Path(tmp))
            self.assertEqual(snapshots, [])
            self.assertIn('hash', errors[0])

    def test_refresh_delegates_and_uses_new_batch_each_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('gap_tracker.dashboard_data.subprocess.run', return_value=Mock(returncode=1, stderr='network unavailable')) as run:
                first = refresh_current(Path(tmp))
                second = refresh_current(Path(tmp))
            self.assertNotEqual(first['batch'], second['batch'])
            self.assertIn('gap_tracker.current', run.call_args.args[0])
            self.assertEqual(first['returncode'], 1)
            self.assertEqual(first['error'], 'network unavailable')


@unittest.skipUnless((ROOT / "data/processed/wayback/2025-03/metrics.json").exists(), "Local research data not bundled")
class DashboardUITests(unittest.TestCase):
    def test_read_only_filters_and_explicit_refresh(self):
        from streamlit.testing.v1 import AppTest
        with patch('gap_tracker.dashboard_data.refresh_current', return_value={
            'returncode': 0, 'categories': {}, 'batch': 'test-only'}) as refresh:
            app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=45)
            self.assertFalse(app.exception)
            refresh.assert_not_called()
            app.sidebar.selectbox[0].select('Women / Jeans').run(timeout=45)
            next(w for w in app.multiselect if w.label == 'Snapshot scope').set_value(['Current', 'Historical']).run(timeout=45)
            app.text_input[0].set_value('jeans').run(timeout=45)
            self.assertFalse(app.exception)
            refresh.assert_not_called()
            app.sidebar.button[0].click().run(timeout=45)
            refresh.assert_called_once()
            self.assertFalse(app.exception)

    def test_refresh_failure_visible(self):
        from streamlit.testing.v1 import AppTest
        with patch('gap_tracker.dashboard_data.refresh_current', return_value={
            'returncode': 1, 'categories': {}, 'error': '/Users/example/private/record.json: test failure'}):
            app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=45)
            app.sidebar.button[0].click().run(timeout=45)
            self.assertFalse(app.exception)
            self.assertTrue(any('incomplete' in e.value for e in app.error))
            self.assertFalse(app.json)
            displayed = ' '.join(str(e.value) for group in (app.markdown, app.caption, app.warning, app.error) for e in group)
            self.assertNotIn('/Users/', displayed)
            self.assertNotIn('Historical (initial study)', displayed)


class DailyPresentationTests(unittest.TestCase):
    def test_latest_per_day_without_pooling_categories_or_scopes(self):
        from gap_tracker.dashboard_data import daily_snapshots
        def snapshot(day, time, category='Jeans', scope='All reported pages'):
            return {'observed_at': f'{day}T{time}+00:00', 'scope': scope,
                    'metrics': {'snapshot_date': day, 'category': category}}
        early = snapshot('2026-09-25', '10:00:00')
        late = snapshot('2026-09-25', '10:05:00')
        other = snapshot('2026-09-25', '10:01:00', 'T-Shirts')
        legacy = snapshot('2026-09-25', '10:02:00', scope='First page only')
        tomorrow = snapshot('2026-09-26', '10:00:00')
        inputs = [late, early, other, legacy, tomorrow]
        result = daily_snapshots(inputs)
        self.assertEqual(len(result), 4)
        self.assertNotIn(early, result)
        self.assertIn(late, result)
        self.assertIn(legacy, result)
        self.assertEqual(len(inputs), 5)

class PortableSnapshotTests(unittest.TestCase):
    def test_historical_paths_use_supplied_repository(self):
        for stored_path in ('data/raw/wayback/example', '/Users/old/checkout/data/raw/wayback/example'):
            with self.subTest(stored_path=stored_path), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                folder = root / 'data/processed/wayback/example'
                raw = root / 'data/raw/wayback/example'
                folder.mkdir(parents=True)
                raw.mkdir(parents=True)
                payload = b'{"ccName": "Blue"}'
                (raw / 'products.json').write_bytes(payload)
                rows = [{'product_name': 'Jeans', 'style_id': '1', 'product_id': '12',
                         'original_price': '100', 'current_price': '70', 'discount_pct': '30',
                         'promo_text': None, 'product_url': None, 'raw_file': 'products.json',
                         'raw_pointer': '', 'provenance': {'observed_at': '2025-01-01T00:00:00+00:00',
                         'evidence_sha256': hashlib.sha256(payload).hexdigest()}}]
                # Match the parser's nonempty pointer format.
                payload = b'{"color":{"ccName":"Blue"}}'
                (raw / 'products.json').write_bytes(payload)
                rows[0]['raw_pointer'] = '/color'
                rows[0]['provenance']['evidence_sha256'] = hashlib.sha256(payload).hexdigest()
                body = json.dumps(rows).encode()
                (folder / 'observations.json').write_bytes(body)
                (folder / 'metrics.json').write_text(json.dumps({'source': 'gap_wayback', 'input': {'sha256': hashlib.sha256(body).hexdigest()}}))
                (folder / 'validation.json').write_text(json.dumps({'metrics_eligible': True, 'raw_snapshot': stored_path}))
                snapshots, errors = load_snapshots(root)
                self.assertFalse(errors)
                self.assertEqual(snapshots[0]['raw'], raw)
                self.assertEqual(evidence_rows(snapshots[0])[0]['Color'], 'Blue')
