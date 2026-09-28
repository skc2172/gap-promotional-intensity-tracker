"""Resumable archive discovery and evidence collection, separate from live refresh.

No date bounds: API captures are indexed without time collapsing; HTML discovery
uses monthly representatives. Unfiltered category captures only. No live fallback.
"""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from gap_tracker.categories import CATEGORIES, category_config
from gap_tracker.wayback import CDX, confirmed_timestamp
from gap_tracker.archive_http import fetch

ROOT = Path('data/raw/backfill-discovery')
API_PATHS = ('/commerce/search/products/v2/cc', '/v2/catalog_search_products/v2/category_products')


def eligible(url, key, api=True):
    config = category_config(key)
    u = urlsplit(url)
    q = parse_qs(u.query, keep_blank_values=True)
    if q.get('cid') != [config['category_id']] or u.fragment:
        return False
    if api:
        allowed = {'brand', 'market', 'cid', 'locale', 'pageSize', 'ignoreInventory',
                   'includeMarketingFlagsDetails', 'pageNumber', 'department', 'mlink', 'vendor',
                   'client_id', 'session_id', 'enableDynamicFacets', 'enableDynamicPhoto'}
        return (u.hostname == 'api.gap.com' and u.path in API_PATHS
                and not q.keys() - allowed and q.get('brand') == ['gap']
                and q.get('market') == ['us'] and q.get('locale') == ['en_US']
                and q.get('department', [config['department_id']]) == [config['department_id']]
                and q.get('pageNumber', ['0']) == ['0']
                and q.get('ignoreInventory', ['false']) == ['false'])
    allowed = {'cid', 'bc', 'cl', 'nav', 'mlink', 'department', 'cookieInitializationAttempted'}
    return (u.hostname in {'www.gap.com', 'gap.com'}
            and u.path in {urlsplit(config['source_url']).path, '/browse/category.do'}
            and not q.keys() - allowed
            and q.get('department', [config['department_id']]) == [config['department_id']])


def read_index(path):
    data = json.loads(path.read_bytes())
    if not isinstance(data, list):
        raise ValueError('CDX response is not a record array')
    if not data:
        return []
    if (not isinstance(data[0], list) or not {'timestamp', 'original', 'digest'} <= set(data[0])
            or any(not isinstance(r, list) or len(r) != len(data[0]) for r in data[1:])):
        raise ValueError('Invalid CDX record structure')
    return [dict(zip(data[0], r)) for r in data[1:]]


def discover(key, start=None, end=None, index_root=ROOT):
    config = category_config(key)
    logs = []
    for name, endpoint in zip(('legacy-api-full', 'current-api-full'), API_PATHS):
        path = index_root / key / (name + '.json')
        params = {'url': 'api.gap.com' + endpoint + '*', 'output': 'json',
                  'filter': ['statuscode:200', f"original:.*[?&]cid={config['category_id']}(&.*)?$"],
                  'fl': 'timestamp,original,mimetype,statuscode,digest', 'limit': '10000'}
        if start is not None:
            params.update({'from': start.strftime('%Y%m%d'), 'to': end.strftime('%Y%m%d')})
        meta = fetch(CDX, path, params)
        records, error = [], meta.get('error')
        if meta.get('status_code') == 200:
            try:
                records = read_index(path)
            except (ValueError, TypeError, OSError) as exc:
                error = str(exc)
        else:
            error = error or f"CDX HTTP {meta.get('status_code')}"
        logs.append({'index': str(path), 'status': meta.get('status_code'), 'records': len(records),
                     'error': error, 'usable': meta.get('status_code') == 200 and not error,
                     'potentially_truncated': len(records) >= 10000})
    (index_root / key / 'discovery-summary.json').write_text(json.dumps(logs, indent=2) + '\n')
    return logs


def collect_candidates(key, index_root=ROOT, raw_root=Path('data/raw/wayback'), represented=None, start=None, end=None):
    records = []
    summary = index_root / key / 'discovery-summary.json'
    indices = {Path(i['index']).name: i for i in json.loads(summary.read_text())} if summary.exists() else {}
    for path in (index_root / key).glob('*api-full.json'):
        index = indices.get(path.name)
        if index and (index.get('status') != 200 or index.get('error') or index.get('usable') is False):
            continue  # Preserve failed response evidence; never parse it as captures.
        records.extend(read_index(path))
    logs, seen = [], set()
    for r in sorted(records, key=lambda r: (r['timestamp'], r['original'])):
        entry = {'candidate': r, 'category_key': key}
        if start is not None and not start.strftime('%Y%m%d') <= r['timestamp'][:8] <= end.strftime('%Y%m%d'):
            entry['status'] = 'outside_requested_period'
        elif represented and (key, r['timestamp']) in represented:
            entry['status'] = 'already_represented'
        elif not eligible(r['original'], key):
            entry['status'] = 'excluded_filtered_or_nonstandard_category_request'
        elif r['digest'] in seen:
            entry['status'] = 'redundant_identical_archive_digest'
        else:
            ts = r['timestamp']
            folder = raw_root / (ts + '-' + key)
            filename = ts + '-' + hashlib.sha256(r['original'].encode()).hexdigest()[:8] + '.json'
            path = folder / filename
            url = f"https://web.archive.org/web/{ts}id_/{r['original']}"
            # Reuse any exact replay already saved by the POC.
            cached = None
            for metadata in raw_root.glob('*/*.request.json'):
                m = json.loads(metadata.read_text())
                if m.get('requested_url') == url and metadata.with_name(metadata.name.removesuffix('.request.json')).exists():
                    cached = (metadata.with_name(metadata.name.removesuffix('.request.json')), m)
                    break
            if cached:
                path, meta = cached
            else:
                meta_path = path.with_suffix(path.suffix + '.request.json')
                if meta_path.exists() and not path.exists():
                    old = json.loads(meta_path.read_text())
                    suffix = hashlib.sha256(meta_path.read_bytes()).hexdigest()[:8]
                    meta_path.rename(meta_path.with_name(meta_path.name + '.' + suffix + '.failed'))
                meta = fetch(url, path)
            if confirmed_timestamp(meta, ts):
                seen.add(r['digest'])
            entry.update(raw_file=str(path), archive_url=url, sha256=meta.get('sha256'),
                         retrieved_at=meta.get('retrieved_at'), status_code=meta.get('status_code'),
                         redirect_url=next((v for k,v in meta.get('headers',{}).items() if k.lower() == 'location'), None),
                         error=meta.get('error'),
                         actual_archive_timestamp=confirmed_timestamp(meta, ts),
                         status='replay_verified' if confirmed_timestamp(meta, ts) else 'replay_unavailable_or_unverified')
        logs.append(entry)
        (index_root / key / 'api-selection.json').write_text(json.dumps(logs, indent=2) + '\n')
    return logs


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--collect', action='store_true')
    cli.add_argument('--html', action='store_true', help='Inspect annual canonical-page representatives across indexed years')
    args = cli.parse_args()
    with ThreadPoolExecutor(max_workers=1) as pool:
        for key, result in zip(CATEGORIES, pool.map(discover, CATEGORIES)):
            print(key, result, flush=True)
    if args.collect:
        with ThreadPoolExecutor(max_workers=1) as pool:
            for key, result in zip(CATEGORIES, pool.map(collect_candidates, CATEGORIES)):
                print(key, 'attempts', len(result), flush=True)

    if args.html:
        for key in CATEGORIES:
            print(key, 'HTML attempts', len(collect_html(key)), flush=True)


def discover_html(key):
    """Canonical legacy URL covers earlier years without tracking-URL explosion."""
    cid = category_config(key)['category_id']
    path = ROOT / key / 'canonical-legacy-page.json'
    meta = fetch(CDX, path, {'url': f'www.gap.com/browse/category.do?cid={cid}',
                           'output': 'json', 'filter': 'statuscode:200',
                           'collapse': 'timestamp:6',
                           'fl': 'timestamp,original,mimetype,statuscode,digest', 'limit': '10000'})
    records = read_index(path) if meta.get('status_code') == 200 else []
    modern = ROOT / key / 'category.json'
    params = {'url': 'www.gap.com/browse/' + CATEGORIES[key][3] + '*', 'output': 'json',
              'filter': ['statuscode:200', f'original:.*[?&]cid={cid}(&.*)?$'],
              'collapse':'timestamp:6', 'fl':'timestamp,original,mimetype,statuscode,digest', 'limit':'1000'}
    modern_meta = fetch(CDX, modern, params)
    if modern_meta.get('status_code') == 200:
        records += read_index(modern)
    return records


def collect_html(key):
    """One earliest unfiltered page per year to inspect structural eras."""
    records = discover_html(key)
    chosen = {}
    for r in sorted(records, key=lambda r: r['timestamp']):
        if eligible(r['original'], key, False):
            chosen.setdefault(r['timestamp'][:4], r)
    selection_file = ROOT / key / 'html-selection.json'
    previous = {a['candidate']['timestamp']: a for a in json.loads(selection_file.read_text())} if selection_file.exists() else {}
    logs = []
    for r in chosen.values():
        if r['timestamp'] in previous:
            logs.append(previous[r['timestamp']])
            continue
        path = ROOT / key / (r['timestamp'] + '-legacy.html')
        url = f"https://web.archive.org/web/{r['timestamp']}id_/{r['original']}"
        meta = fetch(url, path)
        logs.append({'candidate': r, 'raw_file': str(path), 'sha256': meta.get('sha256'),
                     'archive_url': url, 'actual_archive_timestamp': confirmed_timestamp(meta, r['timestamp'])})
        (ROOT / key / 'html-selection.json').write_text(json.dumps(logs, indent=2) + '\n')
    return logs


if __name__ == '__main__':
    main()
