"""As-of resolution and four-section consistency; no network collection."""
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from gap_tracker.dashboard_data import ROOT, as_of_snapshots, load_snapshots, readable_time


class AsOfTests(unittest.TestCase):
    def test_boundaries_arbitrary_dates_and_missing_categories(self):
        def s(category, timestamp):
            return {'metrics': {'category': category}, 'observed_at': timestamp}
        early = s('A', '2026-08-10T00:00:00+00:00')
        late = s('A', '2026-08-31T23:59:59.999999+00:00')
        other = s('B', '2026-08-21T00:00:00+00:00')
        future = s('C', '2026-09-01T00:00:00+00:00')
        offset_future = s('A', '2026-08-31T23:00:00-04:00')
        rows = [future, late, other, early, offset_future]
        eligible, latest = as_of_snapshots(rows, date(2026, 8, 31))
        self.assertEqual(eligible, [early, other, late])
        self.assertEqual(latest, {'A': late, 'B': other})
        self.assertEqual(as_of_snapshots(rows, date(2026, 8, 30))[1], {'A': early, 'B': other})
        self.assertEqual(as_of_snapshots(rows, date(2026, 8, 1)), ([], {}))
        self.assertEqual(len(rows), 5)

    def test_dashboard_dates_consistency_and_evidence(self):
        from streamlit.testing.v1 import AppTest
        snapshots, errors = load_snapshots()
        self.assertFalse(errors)
        charts = []
        with patch('gap_tracker.dashboard_data.refresh_current') as refresh, patch('streamlit.altair_chart', side_effect=lambda c, **kw: charts.append(c)):
            app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=45)
            self.assertFalse(app.exception)
            self.assertEqual(app.date_input[0].value, date.today())
            self.assertEqual(app.date_input[0].max, date.today())
            self.assertEqual(app.date_input[0].min, date(2023, 7, 16))
            previous = {s['metrics']['category']: s for s in snapshots if s['metrics']['source']=='gap_current'}
            self.assertEqual(as_of_snapshots(snapshots, date.today())[1], previous)
            self.assertIn('Current promotional picture', app.subheader[0].value)
            for cutoff in (date.today(), date(2026, 8, 31), date(2023, 7, 16)):
                charts.clear()
                app.date_input[0].set_value(cutoff).run(timeout=45)
                self.assertFalse(app.exception)
                eligible, latest = as_of_snapshots(snapshots, cutoff)
                if cutoff != date.today():
                    self.assertIn(cutoff.strftime('%b %d, %Y'), app.subheader[0].value)
                self.assertTrue(all(d <= cutoff.isoformat() for d in charts[0].data['Date']))
                comparison = charts[1].data
                self.assertEqual(set(comparison['Category']), set(latest))
                expected = []
                for category in sorted(latest):
                    m = latest[category]['metrics']
                    expected.extend([f"{100*m['share_discounted']:.1f}%", f"{m['median_discount_pct_among_discounted']:.1f}%"])
                    row = comparison[comparison['Category']==category].iloc[0]
                    self.assertEqual(row['Observed UTC'], latest[category]['observed_at'])
                    self.assertEqual(row['Discount Breadth'], 100*m['share_discounted'])
                self.assertEqual([m.value for m in app.metric], expected)
                evidence = [w for w in app.selectbox if w.label=='Evidence snapshot']
                if 'Men / Jeans' in latest:
                    self.assertEqual(evidence[0].value['id'], latest['Men / Jeans']['id'])
                    candidates = [s for s in reversed(eligible) if s['metrics']['category']=='Men / Jeans']
                    self.assertEqual(len(evidence[0].options), len(candidates))
                    for option, snapshot in zip(evidence[0].options, candidates):
                        self.assertTrue(option.startswith(readable_time(snapshot['observed_at'])))
                else:
                    self.assertFalse(evidence)
                    self.assertTrue(any('Unavailable' in i.value for i in app.info))
                    self.assertEqual(sum('Unavailable' in m.value for m in app.markdown), 3)
            app.date_input[0].set_value(date(2026, 8, 31)).run(timeout=45)
            e = next(w for w in app.selectbox if w.label=='Evidence snapshot')
            e.select_index(len(e.options)-1).run(timeout=45)
            app.date_input[0].set_value(date.today()).run(timeout=45)
            e = next(w for w in app.selectbox if w.label=='Evidence snapshot')
            self.assertEqual(e.value['id'], previous['Men / Jeans']['id'])
            app.date_input[0].set_value(date.today()+timedelta(days=1)).run(timeout=45)
            self.assertLessEqual(app.date_input[0].value, date.today())
            self.assertFalse(app.exception)
            refresh.assert_not_called()
