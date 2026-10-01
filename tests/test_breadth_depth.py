"""Paired historical breadth/depth comparison and scatter presentation."""
import unittest
from datetime import date
from unittest.mock import patch
from gap_tracker.dashboard_data import ROOT, historical_breadth_depth


def snapshot(id, breadth=.8, depth=40, source='gap_wayback', category='Men / Jeans', day='2026-01-01'):
    return {'id':id,'observed_at':day+'T12:00:00+00:00',
            'metrics':{'category':category,'source':source,'share_discounted':breadth,
                       'median_discount_pct_among_discounted':depth}}


class BreadthDepthTests(unittest.TestCase):
    def setUp(self):
        self.current = snapshot('current', source='gap_current', day='2026-09-27')

    def test_both_thresholds_same_observation_and_equality(self):
        rows=[snapshot('breadth-only',.9,30),snapshot('depth-only',.7,50),
              snapshot('equal'),snapshot('both',.9,50),snapshot('neither',.6,20)]
        self.assertEqual(historical_breadth_depth(self.current,rows),(2,5))

    def test_excludes_missing_other_categories_current_self_and_later(self):
        rows=[snapshot('missing-b',None,50),snapshot('missing-d',.9,None),snapshot('nan',float('nan'),50),
              snapshot('other',category='Women / Jeans'),self.current,
              snapshot('direct',source='gap_current'),snapshot('later',day='2026-09-28'),
              snapshot('same-time',day='2026-09-27'),snapshot('valid')]
        self.assertEqual(historical_breadth_depth(self.current,rows),(1,1))

    def test_no_history_and_unavailable_benchmark(self):
        self.assertEqual(historical_breadth_depth(self.current,[]),(0,0))
        for benchmark in (None,snapshot('historical'),snapshot('missing',None,40,source='gap_current')):
            self.assertIsNone(historical_breadth_depth(benchmark,[snapshot('old')]))

    def test_zero_depth_is_not_missing(self):
        self.assertEqual(historical_breadth_depth(snapshot('now',0,0,'gap_current',day='2026-09-27'),[snapshot('old',0,0)]),(1,1))

    def test_view_uses_same_filtered_data_and_preserves_over_time(self):
        from streamlit.testing.v1 import AppTest
        charts=[]
        with patch('streamlit.altair_chart',side_effect=lambda c,**kw:charts.append(c)), patch('gap_tracker.dashboard_data.refresh_current') as refresh, patch('gap_tracker.dashboard_data.update_historical_archive') as archive:
            app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=45)
            self.assertFalse(app.exception)
            original=charts[0].to_dict()
            original_data=charts[0].data.copy()
            charts.clear()
            next(r for r in app.radio if r.label=='View').set_value('Breadth vs. Depth').run(timeout=45)
            self.assertFalse(app.exception)
            scatter=charts[0];spec=scatter.to_dict()
            self.assertTrue(scatter.data.equals(original_data[original_data['Category']=='Men / Jeans']))
            self.assertEqual(spec['mark']['type'],'point')
            self.assertEqual(spec['encoding']['x']['field'],'Discount Breadth')
            self.assertEqual(spec['encoding']['y']['field'],'Median Discount Depth')
            self.assertEqual(len(spec['encoding']['tooltip']),7)
            self.assertTrue(any('historical observations combined breadth and depth at or above current levels.' in m.value for m in app.markdown))
            self.assertTrue(any('Current vs. available history' in m.value for m in app.markdown))
            self.assertTrue(any(m.value.startswith('Current: ') and '% median depth' in m.value for m in app.markdown))
            charts.clear()
            app.sidebar.selectbox[0].select('Women / Jeans').run(timeout=45)
            self.assertEqual(set(charts[0].data['Category']), {'Women / Jeans'})
            self.assertTrue(charts[0].data.equals(original_data[original_data['Category']=='Women / Jeans']))
            charts.clear()
            next(w for w in app.multiselect if w.label=='Snapshot scope').set_value(['Historical']).run(timeout=45)
            self.assertEqual(set(charts[0].data['Observation type']), {'Historical'})
            next(w for w in app.multiselect if w.label=='Snapshot scope').set_value(['Current', 'Historical']).run(timeout=45)
            app.sidebar.selectbox[0].select('Men / Jeans').run(timeout=45)
            charts.clear()
            app.date_input[0].set_value(date(2026,8,31)).run(timeout=45)
            self.assertTrue(all(d<='2026-08-31' for d in charts[0].data['Date']))
            self.assertTrue(any('Historical comparison unavailable' in m.value for m in app.markdown))
            charts.clear()
            app.date_input[0].set_value(date.today()).run(timeout=45)
            charts.clear()
            next(r for r in app.radio if r.label=='View').set_value('Over time').run(timeout=45)
            self.assertEqual(charts[0].to_dict(),original)
            refresh.assert_not_called();archive.assert_not_called()
