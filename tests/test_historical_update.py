"""Archive updates use real normalization/metrics gates with mocked transport."""
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from gap_tracker.backfill import discover, collect_candidates
from gap_tracker.backfill_publish import BASIS
from gap_tracker.dashboard_data import ROOT, load_snapshots, as_of_snapshots
from gap_tracker.historical_update import update_archive


class HistoricalUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.start, self.end = date(2026, 8, 1), date(2026, 8, 31)
        self.url = 'https://api.gap.com/commerce/search/products/v2/cc?brand=gap&market=us&locale=en_US&cid=6998&department=75&pageNumber=0'
        self.ts = '20260815120000'
        self.payload = {'locale':'en_US', 'categories':[{'categoryId':'6998','ccList':[{'styleId':'s','ccId':'c'}]}],
                        'products':[{'styleId':'s','styleName':'Jeans','styleColors':[{'ccId':'c','ccName':'Blue','regularPrice':'100','effectivePrice':'70'}]}]}

    def attempt(self, reviewed=True):
        path = self.root/'candidate.json'
        path.write_text(json.dumps(self.payload))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        attempt = dict(status='replay_verified', actual_archive_timestamp=self.ts,
                       candidate={'original':self.url,'timestamp':self.ts}, raw_file=str(path), sha256=sha,
                       archive_url=f'https://web.archive.org/web/{self.ts}id_/{self.url}', retrieved_at='2026-09-27T00:00:00+00:00')
        reviews = [dict(archive_timestamp=self.ts, source_url=self.url, sha256=sha, price_basis=BASIS,
                        rationale='Reviewed archived pricing evidence', evidence=[{'file':'candidate.json','sha256':sha}])] if reviewed else []
        (self.root/'docs').mkdir(exist_ok=True)
        (self.root/'docs/backfill-price-reviews.json').write_text(json.dumps(reviews))
        return attempt

    def run_update(self, attempt):
        with patch('gap_tracker.historical_update.discover', return_value=[{'status':200}]) as discover_mock, patch('gap_tracker.historical_update.collect_candidates', side_effect=lambda key,*args: [attempt] if key=='men-jeans' else []):
            result = update_archive(self.start, self.end, self.root)
            self.assertEqual(discover_mock.call_count,4)
            self.assertTrue(all(c.args[1:3]==(self.start,self.end) for c in discover_mock.call_args_list))
            return result

    def test_append_provenance_dedup_and_as_of_without_changing_current(self):
        existing = next(s for s in load_snapshots()[0] if s['metrics']['source']=='gap_current')
        for filename in ('metrics.json','observations.json','validation.json'):
            target=self.root/'data/processed'/existing['id']/filename
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(existing['folder']/filename,target)
        raw=self.root/'data/raw'/existing['id']; raw.mkdir(parents=True)
        shutil.copyfile(existing['raw']/'manifest.json',raw/'manifest.json')
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        attempt=self.attempt()
        self.assertEqual(self.run_update(attempt)['added'],1)
        for p,body in before.items(): self.assertEqual(p.read_bytes(),body)
        snapshots, errors=load_snapshots(self.root); self.assertFalse(errors)
        archive=next(s for s in snapshots if s['metrics']['source']=='gap_wayback')
        self.assertEqual(archive['observed_at'],'2026-08-15T12:00:00+00:00')
        self.assertEqual(archive['rows'][0]['provenance']['evidence_url'],attempt['archive_url'])
        self.assertEqual(archive['metrics']['input']['snapshot_id'],archive['folder'].name)
        self.assertEqual(as_of_snapshots(snapshots,self.end)[1]['Men / Jeans']['id'],archive['id'])
        self.assertNotIn('Men / Jeans',as_of_snapshots(snapshots,date(2026,8,14))[1])
        self.assertEqual(self.run_update(attempt)['added'],0)
        self.assertEqual(as_of_snapshots(load_snapshots(self.root)[0],self.end),as_of_snapshots(snapshots,self.end))

    def test_invalid_missing_prices_unreviewed_and_missing_records_rejected(self):
        for kind in ('missing_price','missing_record','unreviewed','bad_hash'):
            with self.subTest(kind=kind):
                self.payload['products'][0]['styleColors'][0]['effectivePrice']='70'
                self.payload['categories'][0]['ccList'][0]['ccId']='c'
                if kind=='missing_price': self.payload['products'][0]['styleColors'][0]['effectivePrice']=None
                if kind=='missing_record': self.payload['categories'][0]['ccList'][0]['ccId']='absent'
                attempt=self.attempt(reviewed=kind!='unreviewed')
                if kind=='bad_hash': attempt['sha256']='bad'
                self.assertEqual(self.run_update(attempt)['added'],0)
                self.assertFalse(load_snapshots(self.root)[0])

    def test_discovery_bounds_and_already_represented_not_fetched(self):
        index=self.root/'indices'
        def fetch(url,path,params):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('[]')
            self.assertEqual(params['from'],'20260801'); self.assertEqual(params['to'],'20260831')
            return {'status_code':200}
        with patch('gap_tracker.backfill.fetch',side_effect=fetch):
            discover('men-jeans',self.start,self.end,index)
        p=index/'men-jeans/legacy-api-full.json'
        p.write_text(json.dumps([['timestamp','original','digest'],[self.ts,self.url,'digest']]))
        with patch('gap_tracker.backfill.fetch') as network:
            attempts=collect_candidates('men-jeans',index,self.root/'raw',{('men-jeans',self.ts)},self.start,self.end)
            network.assert_not_called()
            self.assertEqual(attempts[0]['status'],'already_represented')

    def test_empty_and_failed_discovery_are_distinct(self):
        with patch('gap_tracker.historical_update.discover',return_value=[{'status':200}]), patch('gap_tracker.historical_update.collect_candidates',return_value=[]):
            self.assertEqual(update_archive(self.start,self.end,self.root),{'added':0,'incomplete':False})
        with patch('gap_tracker.historical_update.discover',side_effect=OSError('offline')):
            self.assertEqual(update_archive(self.start,self.end,self.root),{'added':0,'incomplete':True})

    def test_invalid_range(self):
        with self.assertRaises(ValueError): update_archive(self.end,self.start,self.root)

    def test_ui_update_is_explicit_separate_and_keeps_as_of(self):
        from streamlit.testing.v1 import AppTest
        with patch('gap_tracker.dashboard_data.update_historical_archive',return_value={'added':0,'incomplete':False}) as archive, patch('gap_tracker.dashboard_data.refresh_current') as live:
            app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=45)
            self.assertFalse(app.exception)
            archive.assert_not_called(); live.assert_not_called()
            app.date_input[0].set_value(date(2026,8,31)).run(timeout=45)
            next(d for d in app.date_input if d.label=='Historical start date').set_value(date(2026,8,1)).run(timeout=45)
            next(d for d in app.date_input if d.label=='Historical end date').set_value(date(2026,8,31)).run(timeout=45)
            next(b for b in app.button if b.label=='Update Historical Archive').click().run(timeout=45)
            archive.assert_called_once_with(date(2026,8,1),date(2026,8,31))
            live.assert_not_called()
            self.assertEqual(app.date_input[0].value,date(2026,8,31))
            self.assertFalse(app.exception)
            self.assertTrue(any('no new valid observations' in i.value for i in app.info))

    def test_failed_or_malformed_indices_are_preserved_and_skipped(self):
        for status, body in ((503, '<html>Temporarily Offline</html>'), (429, 'rate limited'), (200, '<html>not JSON</html>'), (200, '{}')):
            with self.subTest(status=status,body=body):
                index=self.root/str(status)
                def fetch(url,path,params):
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(body)
                    return {'status_code':status}
                with patch('gap_tracker.backfill.fetch',side_effect=fetch):
                    logs=discover('men-jeans',self.start,self.end,index)
                self.assertTrue(all(not i['usable'] and i['error'] for i in logs))
                self.assertEqual(collect_candidates('men-jeans',index),[])
                self.assertEqual((index/'men-jeans/legacy-api-full.json').read_text(),body)
                with patch('gap_tracker.historical_update.discover',return_value=logs), patch('gap_tracker.historical_update.collect_candidates',return_value=[]):
                    self.assertTrue(update_archive(self.start,self.end,self.root)['incomplete'])

    def test_partial_additions_do_not_hide_search_failure(self):
        from streamlit.testing.v1 import AppTest
        with patch('gap_tracker.dashboard_data.update_historical_archive',return_value={'added':1,'incomplete':True}):
            app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=45)
            next(b for b in app.button if b.label=='Update Historical Archive').click().run(timeout=45)
            self.assertFalse(app.exception)
            self.assertTrue(any('Archive search could not be completed' in w.value for w in app.warning))
            self.assertFalse(app.success)
