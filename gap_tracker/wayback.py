"""Bounded, resumable Wayback evidence collection for three research periods.

Downloads archive HTML only. Never runs scripts or falls back to live Gap.
"""
import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests

PERIODS = ('2025-03', '2025-09', '2026-03')
CDX = 'https://web.archive.org/cdx/search/cdx'
ROOT = Path('data/raw/wayback')


def same_category(url):
    """Accept the whole category, not style/color filters or malformed URLs."""
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    allowed = {'cid', 'bc', 'cl', 'nav', 'mlink', 'department', 'cookieInitializationAttempted'}
    return (parsed.hostname in {'gap.com', 'www.gap.com'}
            and parsed.path in {'/browse/women/jeans', '/browse/category.do'}
            and query.get('cid') == ['5664'] and not (query.keys() - allowed)
            and query.get('cookieInitializationAttempted', ['true']) == ['true']
            and query.get('department', ['136']) == ['136'] and not parsed.fragment)


def ranked_candidates(index, period):
    anchor = datetime.strptime(period + '-15T12:00:00', '%Y-%m-%dT%H:%M:%S')
    if not index:
        return []
    records = [dict(zip(index[0], row)) for row in index[1:]]
    candidates = [r for r in records if r.get('statuscode') == '200'
                  and r.get('mimetype') == 'text/html' and same_category(r['original'])]
    return sorted(candidates, key=lambda r: (
        abs(datetime.strptime(r['timestamp'], '%Y%m%d%H%M%S') - anchor),
        r['timestamp'], r['original']))


def fetch(url, body_path, params=None):
    """Cache exact requests and preserve response bodies, including errors."""
    meta_path = body_path.with_suffix(body_path.suffix + '.request.json')
    expected = requests.Request('GET', url, params=params).prepare().url
    if body_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta['requested_url'] != expected:
            raise ValueError('Cached request differs; use another evidence directory')
        if hashlib.sha256(body_path.read_bytes()).hexdigest() != meta['sha256']:
            raise ValueError('Cached evidence was modified')
        return meta
    body_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {'requested_url': expected, 'retrieved_at': datetime.now(timezone.utc).isoformat()}
    try:
        response = requests.get(url, params=params, timeout=(10, 45), allow_redirects=False)
        body_path.write_bytes(response.content)
        meta.update(status_code=response.status_code, url=response.url,
                    headers={k: v for k, v in response.headers.items() if 'cookie' not in k.lower()},
                    sha256=hashlib.sha256(response.content).hexdigest())
    except requests.RequestException as exc:
        meta['error'] = str(exc)
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    return meta


def confirmed_timestamp(meta, expected):
    """Verify replay timestamp rather than trusting a requested replay URL."""
    headers = {k.lower(): v for k, v in meta.get('headers', {}).items()}
    if meta.get('status_code') != 200 or not headers.get('memento-datetime'):
        return None
    actual = parsedate_to_datetime(headers['memento-datetime']).strftime('%Y%m%d%H%M%S')
    return actual if actual == expected else None


def same_category_api(url):
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    allowed = {'brand', 'market', 'cid', 'locale', 'pageSize', 'ignoreInventory',
               'includeMarketingFlagsDetails', 'pageNumber', 'department', 'mlink', 'vendor'}
    return (parsed.hostname == 'api.gap.com'
            and parsed.path == '/commerce/search/products/v2/cc'
            and query.get('cid') == ['5664'] and query.get('brand') == ['gap']
            and query.get('market') == ['us'] and query.get('locale') == ['en_US']
            and query.get('department') == ['136'] and query.get('pageNumber') == ['0']
            and not (query.keys() - allowed))


def collect(period, root=ROOT):
    if period not in PERIODS:
        raise ValueError('Only the three requested periods are supported')
    folder = root / period
    anchor = datetime.strptime(period + '-15T12:00:00', '%Y-%m-%dT%H:%M:%S')
    bounds = {'from': (anchor - timedelta(days=45)).strftime('%Y%m%d'),
              'to': (anchor + timedelta(days=45)).strftime('%Y%m%d')}
    # Refine the earlier monthly-collapsed discovery index so nearest is exact.
    params = {'url': 'www.gap.com/browse/women/jeans*', 'output': 'json',
              'filter': 'statuscode:200', **bounds}
    meta = fetch(CDX, folder / 'index.json', params)
    if meta.get('status_code') != 200:
        raise ValueError(f'Archive index unavailable; see {folder}')
    candidates = ranked_candidates(json.loads((folder / 'index.json').read_bytes()), period)
    selection = {'requested_target_period': period, 'target_anchor_utc': anchor.isoformat() + 'Z',
                 'search_bounds': bounds, 'selection_rule': 'Nearest to 15th at noon UTC; up to three distinct bodies among unfiltered category URLs',
                 'candidate_count': len(candidates), 'attempts': []}
    seen = set()
    for candidate in candidates:
        if candidate['digest'] in seen:
            continue
        seen.add(candidate['digest'])
        timestamp, original = candidate['timestamp'], candidate['original']
        key = timestamp + '-' + hashlib.sha256(original.encode()).hexdigest()[:8]
        archive_url = f'https://web.archive.org/web/{timestamp}id_/{original}'
        # Reuse an exact response saved before the interruption, when available.
        old = Path('data/raw/wayback-discovery') / period
        if (old / 'request.json').exists():
            saved = json.loads((old / 'request.json').read_text())
        else:
            saved = {}
        if saved.get('url') == archive_url:
            path = old / 'page.html'
            if hashlib.sha256(path.read_bytes()).hexdigest() != saved['sha256']:
                raise ValueError('Previously saved archive body hash mismatch')
            replay = {**saved, 'status_code': saved['status']}
        else:
            path = folder / (key + '.html')
            replay = fetch(archive_url, path)
        selection['attempts'].append({'candidate': candidate, 'raw_file': str(path),
            'archive_url': archive_url, 'actual_archive_timestamp': confirmed_timestamp(replay, timestamp),
            'retrieved_at': replay.get('retrieved_at'), 'status_code': replay.get('status_code'),
            'sha256': replay.get('sha256'), 'error': replay.get('error')})
        (folder / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
        if len(selection['attempts']) >= 3:
            break
    # This endpoint is named by the archived HTML, not assumed from the live API.
    api_params = {'url': 'api.gap.com/commerce/search/products/v2/cc*', 'output': 'json',
                  'filter': ['statuscode:200', 'original:.*[?&]cid=5664(&.*)?$'], **bounds}
    api_meta = fetch(CDX, folder / 'product-api-index.json', api_params)
    selection['archived_product_api_index_status'] = api_meta.get('status_code')
    selection['archived_product_api_index_file'] = str(folder / 'product-api-index.json')
    selection['api_attempts'] = []
    if api_meta.get('status_code') == 200:
        index = json.loads((folder / 'product-api-index.json').read_bytes())
        records = [dict(zip(index[0], row)) for row in index[1:]] if index else []
        records = sorted((r for r in records if same_category_api(r['original'])), key=lambda r:
                         abs(datetime.strptime(r['timestamp'], '%Y%m%d%H%M%S') - anchor))
        for candidate in records[:3]:
            ts, original = candidate['timestamp'], candidate['original']
            path = folder / (ts + '-products.json')
            url = f'https://web.archive.org/web/{ts}id_/{original}'
            replay = fetch(url, path)
            selection['api_attempts'].append({'candidate': candidate, 'raw_file': str(path),
                'archive_url': url, 'actual_archive_timestamp': confirmed_timestamp(replay, ts),
                'retrieved_at': replay.get('retrieved_at'), 'status_code': replay.get('status_code'),
                'sha256': replay.get('sha256'), 'error': replay.get('error')})
    (folder / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    print(period, 'candidates', len(candidates), 'attempted', len(selection['attempts']), flush=True)
    return selection


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('period', choices=PERIODS)
    collect(cli.parse_args().period)
