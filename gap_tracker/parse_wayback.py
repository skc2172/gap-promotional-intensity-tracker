"""Offline inspection of archived category HTML, with a fail-closed metrics gate.

The historical HTML pages are client-rendered shells. Preserve page-level evidence
without turning navigation or placeholders into products. A separate API adapter
handles the inspected April 2025 response; metrics require an evidence-backed review.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import csv

from bs4 import BeautifulSoup

from gap_tracker.wayback import PERIODS, ROOT
from gap_tracker.parse import FIELDS, price
from gap_tracker.metrics import write_metrics


def reviewed_basis(review_path, attempt):
    if review_path is None:
        return None
    review = json.loads(review_path.read_text())
    if review['archive_timestamp'] != attempt['actual_archive_timestamp']:
        return None
    if review['price_basis'] != 'displayed_current_vs_retailer_reference' or not review.get('evidence'):
        raise ValueError('Unsupported price-basis review')
    for evidence in review['evidence']:
        if hashlib.sha256(Path(evidence['file']).read_bytes()).hexdigest() != evidence['sha256']:
            raise ValueError('Price-basis evidence hash mismatch')
    return review['price_basis']


def normalize_archived_api(payload, attempt, period, price_basis=None, category_config=None):
    """Adapter for the inspected April 2025 cc response, not a live API call.

    Historical *MarketingFlagsDetails are preserved with their original keys.
    Comparable display semantics are established separately from field parsing.
    """
    config = category_config or {'category_id': '5664', 'category': 'Women / Jeans',
                                 'source_url': 'https://www.gap.com/browse/women/jeans?cid=5664'}
    timestamp = attempt.get('actual_archive_timestamp')
    if not timestamp or payload.get('locale') != 'en_US':
        raise ValueError('Verified archive timestamp and US locale required')
    date = datetime.strptime(timestamp, '%Y%m%d%H%M%S').date().isoformat()
    index = {}
    for pi, product in enumerate(payload['products']):
        for ci, color in enumerate(product['styleColors']):
            key = (product['styleId'], color['ccId'])
            if key in index:
                raise ValueError('Duplicate archived product-color record')
            index[key] = (product, color, f'/products/{pi}/styleColors/{ci}')
    rows, seen = [], set()
    for category in payload['categories']:
        if str(category['categoryId']) != config['category_id']:
            raise ValueError('Wrong archived category')
        for ref in category['ccList']:
            key = (ref['styleId'], ref['ccId'])
            if key in seen:
                continue
            seen.add(key)
            if key not in index:
                raise ValueError('Listed historical color is absent from response')
            product, color, pointer = index[key]
            original, current = price(color.get('regularPrice')), price(color.get('effectivePrice'))
            if original == 0 or (original is not None and current is not None and current > original):
                raise ValueError('Invalid archived price relationship')
            known = original is not None and current is not None
            discount = ((original-current)/original*100).quantize(Decimal('.0001')) if known else None
            flags = color.get('ccLevelMarketingFlags')
            promo = ' | '.join(dict.fromkeys(f['content'] for f in flags or [] if f.get('content'))) or None
            rows.append(dict(zip(FIELDS, [
                date, color['ccId'], product['styleId'], color.get('styleName') or product.get('styleName'),
                config['category'], str(original) if original is not None else None,
                str(current) if current is not None else None,
                str(discount) if discount is not None else None, current < original if known else None,
                promo, 'gap_wayback', config['source_url'],
                f"https://www.gap.com/browse/product.do?pid={color['ccId']}", 'USD',
                Path(attempt['raw_file']).name, pointer, color.get('percentageOff') or None,
                color.get('priceType') or None,
                {'product_color_flags': flags, 'product_color_badges': color.get('ccLevelBadges'),
                 'style_flags': None, 'style_excluded_from_promotion': product.get('excludedFromPromotion'),
                 'ccMarketingFlagsDetails': color.get('ccMarketingFlagsDetails'),
                 'styleMarketingFlagsDetails': product.get('styleMarketingFlagsDetails'),
                 'color_styleMarketingFlagsDetails': color.get('styleMarketingFlagsDetails')},
                price_basis,
                {'observed_at': datetime.strptime(timestamp,'%Y%m%d%H%M%S').isoformat()+'+00:00',
                 'retrieved_at': attempt['retrieved_at'], 'evidence_url': attempt['archive_url'],
                 'original_evidence_url': attempt['candidate']['original'],
                 'evidence_sha256': attempt['sha256'], 'requested_target_period': period,
                 'archive_timestamp': timestamp,
                 'price_fields': {'original_price': 'regularPrice', 'current_price': 'effectivePrice'}},
            ])))
    if not rows:
        raise ValueError('No listed historical product-color records')
    return rows


def inspect_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    scripts = '\n'.join(s.get_text() for s in soup.find_all('script'))
    # Decode Next flight strings as JSON, never execute JavaScript.
    flight = []
    for script in soup.find_all('script'):
        match = re.fullmatch(r'self\.__next_f\.push\((\[.*\])\);?', script.get_text(), re.S)
        if match:
            try:
                value = json.loads(match[1])
                if len(value) == 2 and isinstance(value[1], str):
                    flight.append(value[1])
            except (ValueError, TypeError):
                pass
    decoded = scripts + '\n' + '\n'.join(flight)
    ld_types = []

    def types(value):
        if isinstance(value, dict):
            kind = value.get('@type')
            if isinstance(kind, str):
                ld_types.append(kind)
            elif isinstance(kind, list):
                ld_types.extend(kind)
            for child in value.values():
                types(child)
        elif isinstance(value, list):
            for child in value:
                types(child)

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            types(json.loads(script.get_text()))
        except ValueError:
            ld_types.append('invalid_json')
    breadcrumb = next((s for s in soup.find_all('script', type='application/ld+json')
                       if 'BreadcrumbList' in s.get_text() and 'cid=5664' in s.get_text()
                       and 'Women' in s.get_text() and 'Jeans' in s.get_text()), None)
    product_links = soup.select('a[href*="pid="]')
    cards = soup.select('[data-testid="plp_product-card"]')
    numeric_prices = re.findall(r'"(?:regularPrice|effectivePrice|salePrice|currentPrice)"\s*:\s*"?\d+(?:\.\d+)?', decoded)
    skeletons = len(soup.select('[id="plp-product-card-skeleton"]'))
    messages = []
    header = soup.select_one('[data-testid="desktop-mobile-header"]') or soup.find('header')
    if header:
        for element in header.select('p, a[title], img[alt]'):
            attribute = 'alt' if element.name == 'img' else 'title' if element.has_attr('title') else None
            text = element.get(attribute) if attribute else element.get_text(' ', strip=True)
            if text and re.search(r'%|\boff\b|\bsale\b|\bdiscount\b', text, re.I):
                message = {'scope': 'page_header', 'text': text, 'tag': element.name, 'attribute': attribute}
                if message not in messages:
                    messages.append(message)
    has_product_material = bool(cards or product_links or numeric_prices or 'Product' in ld_types)
    status = ('wrong_or_unverified_category' if breadcrumb is None else
              'unrecognized_product_structure' if has_product_material else 'category_shell_no_product_data')
    return {
        'inspection_status': status,
        'category_identity_verified': breadcrumb is not None,
        'title': soup.title.get_text() if soup.title else None,
        'structure': {'next_flight_chunks': len(flight), 'json_ld_types': sorted(set(ld_types)),
                      'product_links': len(product_links), 'product_cards': len(cards),
                      'numeric_price_fields': len(numeric_prices), 'product_skeletons': skeletons},
        'page_promo_evidence': messages,
        'product_endpoint_referenced': 'https://api.gap.com/commerce/search/products/v2/cc'
            if 'https://api.gap.com/commerce/search/products/v2/cc' in decoded else None,
        'product_parsing_success': False, 'product_observations_extracted': 0,
        'observations': [], 'reference_price_coverage': None, 'current_price_coverage': None,
        'missing_price_rate': None, 'product_promo_coverage': None,
        'observation_unit': None, 'price_basis': None, 'metrics_eligible': False,
        'comparability': 'Not established: no supported archived product-price observations; no historical metrics emitted.',
    }


def analyze(period, root=ROOT, output_root=Path('data/processed/wayback'), review_path=None):
    selection = json.loads((root / period / 'selection.json').read_text())
    inspections = []
    for attempt in selection['attempts']:
        evidence = {k: attempt.get(k) for k in ('raw_file', 'archive_url', 'actual_archive_timestamp', 'retrieved_at', 'sha256')}
        evidence['requested_target_period'] = period
        if attempt['actual_archive_timestamp'] is None:
            inspections.append({'provenance': evidence, 'inspection_status': 'replay_not_verified',
                                'metrics_eligible': False})
            continue
        body = Path(attempt['raw_file']).read_bytes()
        if hashlib.sha256(body).hexdigest() != attempt['sha256']:
            raise ValueError('Archived evidence hash mismatch')
        inspections.append({'provenance': evidence, **inspect_html(body)})
    api_file = Path(selection['archived_product_api_index_file'])
    api_index = json.loads(api_file.read_bytes()) if selection['archived_product_api_index_status'] == 200 else None
    api_inspections, rows = [], []
    for attempt in selection.get('api_attempts', []):
        if not attempt['actual_archive_timestamp']:
            api_inspections.append({'archive_url': attempt['archive_url'], 'status': 'replay_not_verified'})
            continue
        body = Path(attempt['raw_file']).read_bytes()
        if hashlib.sha256(body).hexdigest() != attempt['sha256']:
            raise ValueError('Archived API evidence hash mismatch')
        payload = json.loads(body)
        basis = reviewed_basis(review_path, attempt)
        candidate_rows = normalize_archived_api(payload, attempt, period, basis)
        details = {'archive_timestamp': attempt['actual_archive_timestamp'],
                   'archive_url': attempt['archive_url'], 'raw_file': attempt['raw_file'],
                   'status': 'parsed_product_records_display_semantics_unverified',
                   'product_observations_extracted': len(candidate_rows),
                   'unique_styles': len({r['style_id'] for r in candidate_rows}),
                   'api_total_colors': payload.get('totalColors'), 'pagination': payload.get('pagination'),
                   'personalized_sort': payload.get('personalizedSortRecommenderInfo'),
                   'missing': {k: {'count': sum(r[k] is None for r in candidate_rows),
                                   'rate': sum(r[k] is None for r in candidate_rows) / len(candidate_rows)}
                               for k in ['product_name', 'original_price', 'current_price', 'promo_text']},
                   'reference_price_coverage': sum(r['original_price'] is not None for r in candidate_rows)/len(candidate_rows),
                   'current_price_coverage': sum(r['current_price'] is not None for r in candidate_rows)/len(candidate_rows),
                   'product_parsing_success': True, 'metrics_eligible': basis is not None}
        if basis:
            details['status'] = 'parsed_price_basis_verified'
        api_inspections.append(details)
        if not rows:
            rows = candidate_rows
    report = {'requested_target_period': period, 'target_anchor_utc': selection['target_anchor_utc'],
              'search_bounds': selection['search_bounds'], 'candidate_count': selection['candidate_count'],
              'nearest_checked_archive_timestamp': inspections[0]['provenance']['actual_archive_timestamp'] if inspections else None,
              'usable_archive_timestamp': None, 'archived_api_candidates': max(len(api_index)-1, 0) if api_index is not None else None,
              'attempts': inspections,
              'api_attempts': api_inspections,
              'normalized_product_observations': len(rows),
              'product_data_alternative_timestamp': rows[0]['provenance']['archive_timestamp'] if rows else None,
              'status': 'no_usable_product_snapshot_in_checked_candidates',
              'metrics_eligible': False,
              'search_limit': 'At most three nearest distinct category HTML bodies, plus archived index of the product endpoint named by those pages. Not an exhaustive archive search.'}
    folder = output_root / period
    folder.mkdir(parents=True, exist_ok=True)
    if rows:
        report['status'] = 'alternative_product_records_available_display_comparability_unverified'
        report['metrics_withheld_reason'] = 'Historical API field pairs and color identities are preserved, but archived display mapping is not yet verified.'
        if rows[0]['price_basis']:
            report.update(status='dated_alternative_price_metrics_available', metrics_eligible=True,
                          usable_archive_timestamp=rows[0]['provenance']['archive_timestamp'],
                          price_basis_review=str(review_path),
                          comparability='Price concepts and product-color unit supported; date, assortment, coverage, ranking, and offer eligibility differ. Not a matched-panel trend.')
            report.pop('metrics_withheld_reason')
    # An empty array is a failed extraction, not a zero-product category claim.
    (folder / 'observations.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    with (folder / 'observations.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                          for k, v in row.items()} for row in rows)
    (folder / 'validation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    if report['metrics_eligible']:
        metrics_path = write_metrics(folder / 'observations.json')
        metrics = json.loads(metrics_path.read_text())
        metrics['historical_context'] = {
            'requested_target_period': period,
            'actual_archive_timestamp': report['usable_archive_timestamp'],
            'date_is_outside_requested_month': not rows[0]['snapshot_date'].startswith(period),
            'comparability': report['comparability'],
        }
        metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + '\n')
    elif (folder / 'metrics.json').exists():
        # A stricter rerun must not leave an apparently current, eligible metric file.
        (folder / 'metrics.json').rename(folder / 'metrics.previous-unverified.json')
    print(period, report['nearest_checked_archive_timestamp'], [(a['inspection_status']) for a in inspections],
          'archived API candidates:', report['archived_api_candidates'])
    return report


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('period', choices=PERIODS)
    cli.add_argument('--price-basis-review', type=Path)
    args = cli.parse_args()
    analyze(args.period, review_path=args.price_basis_review)
