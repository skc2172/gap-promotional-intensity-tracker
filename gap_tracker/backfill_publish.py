"""Offline, review-gated historical publication; no network or live fallbacks."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from gap_tracker.backfill import ROOT, eligible
from gap_tracker.categories import CATEGORIES, category_config
from gap_tracker.parse import FIELDS
from gap_tracker.parse_wayback import normalize_archived_api
from gap_tracker.metrics import calculate, write_metrics

BASIS = 'displayed_current_vs_retailer_reference'


def verified_review(attempt, reviews):
    for review in reviews:
        if (review['archive_timestamp'] == attempt['actual_archive_timestamp']
                and review['sha256'] == attempt['sha256']
                and review['source_url'] == attempt['candidate']['original']):
            if review['price_basis'] != BASIS or not review.get('rationale') or not review.get('evidence'):
                raise ValueError('Incomplete price-basis review')
            for evidence in review['evidence']:
                if hashlib.sha256(Path(evidence['file']).read_bytes()).hexdigest() != evidence['sha256']:
                    raise ValueError('Price-basis evidence hash mismatch')
            return review
    return None


def representative(candidates):
    """One per category/month: best observed price coverage, then sample, then date.

    Does not rank on discount intensity. Keep distinct price/assortment states.
    """
    groups = defaultdict(list)
    for candidate in candidates:
        groups[(candidate['category_key'], candidate['rows'][0]['snapshot_date'][:7])].append(candidate)
    selected = []
    for group in groups.values():
        selected.append(sorted(group, key=lambda c: (-c['coverage'], -len(c['rows']), c['timestamp']))[0])
    return sorted(selected, key=lambda c: (c['category_key'], c['timestamp']))


def publish(review_path=Path('docs/backfill-price-reviews.json')):
    reviews = json.loads(review_path.read_text()) if review_path.exists() else []
    candidates, audit = [], []
    for key in CATEGORIES:
        path = ROOT / key / 'api-selection.json'
        if not path.exists():
            audit.append({'category_key': key, 'status': 'collection_not_completed'})
            continue
        for attempt in json.loads(path.read_text()):
            entry = {'category_key': key, 'timestamp': attempt['candidate']['timestamp'],
                     'source_url': attempt['candidate']['original'], 'status': attempt['status'],
                     'status_code': attempt.get('status_code'), 'redirect_url': attempt.get('redirect_url'),
                     'error': attempt.get('error')}
            audit.append(entry)
            if attempt['status'] != 'replay_verified':
                continue
            try:
                if not eligible(attempt['candidate']['original'], key):
                    raise ValueError('Not an unfiltered category API capture')
                body = Path(attempt['raw_file']).read_bytes()
                if hashlib.sha256(body).hexdigest() != attempt['sha256']:
                    raise ValueError('Raw archive hash mismatch')
                review = verified_review(attempt, reviews)
                payload = json.loads(body)
                rows = normalize_archived_api(payload, attempt, None, BASIS if review else None, category_config(key))
                coverage = sum(r['original_price'] is not None and r['current_price'] is not None for r in rows)/len(rows)
                entry.update(observations=len(rows), price_coverage=coverage)
                if review is None:
                    entry['status'] = 'prices_parsed_display_basis_not_reviewed'
                    continue
                if coverage == 0:
                    entry['status'] = 'no_paired_prices'
                    continue
                entry['status'] = 'eligible_not_selected_monthly_representative'
                candidates.append({'category_key': key, 'timestamp': attempt['actual_archive_timestamp'],
                                   'rows': rows, 'coverage': coverage, 'payload': payload,
                                   'attempt': attempt, 'review': review, 'audit': entry})
            except (ValueError, KeyError, TypeError, OSError) as exc:
                entry.update(status='parsing_or_review_failed', reason=str(exc))
    previous = {}
    summaries = []
    for item in representative(candidates):
        key, ts, rows = item['category_key'], item['timestamp'], item['rows']
        state = sorted((r['style_id'], r['product_id'], r['original_price'], r['current_price']) for r in rows)
        signature = hashlib.sha256(json.dumps(state).encode()).hexdigest()
        if previous.get(key) == signature:
            item['audit']['status'] = 'redundant_unchanged_observed_price_state'
            continue
        previous[key] = signature
        # The original POC is already dashboard-visible; never publish it twice.
        if ts == '20250411132536' and key == 'women-jeans':
            item['audit']['status'] = 'existing_validated_poc_retained'
            continue
        folder = Path('data/processed/wayback') / (ts + '-' + key)
        folder.mkdir(parents=True, exist_ok=True)
        for row in rows:
            row['provenance']['snapshot_id'] = folder.name
        (folder/'observations.json').write_text(json.dumps(rows, indent=2) + '\n')
        with (folder/'observations.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows({k: json.dumps(v) if isinstance(v, (dict,list)) else v for k,v in row.items()} for row in rows)
        p = item['payload']
        validation = {'metrics_eligible': True, 'source_method': 'archived_category_api',
                      'historical_scope': 'Archived API sample', 'category': category_config(key)['category'],
                      'raw_snapshot': str(Path(item['attempt']['raw_file']).parent.resolve()),
                      'archive_timestamp': ts, 'api_total_colors': p.get('totalColors'),
                      'pagination': p.get('pagination'), 'pages_collected': 1,
                      'products_captured': len(rows), 'price_coverage': item['coverage'],
                      'price_basis_review': item['review'],
                      'comparability': 'Price concepts transferred from the directly verified April 2025 archived frontend via the matching legacy API contract. This is a schema-based inference, not capture-specific rendered-price verification. Single archived response; ranking, grouping, inventory, assortment and coverage differ from current collections.',
                      'research_selected': True,
                      'selection': 'Monthly representative by price coverage, sample size, then earliest timestamp; repeated exact observed price states omitted.'}
        (folder/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
        metrics = json.loads(write_metrics(folder/'observations.json').read_text())
        item['audit']['status'] = 'published'
        summaries.append({**{k: metrics[k] for k in ['snapshot_date','category','total_observations','unique_styles_observed', 'share_discounted','median_discount_pct_among_discounted','share_discounted_at_least_30_pct']},
                          'price_coverage':item['coverage'], 'source_method':'archived_category_api', 'snapshot':str(folder)})
    selected_paths = {r['snapshot'] for r in summaries}
    for prior in Path('data/processed/wayback').glob('*/validation.json'):
        report = json.loads(prior.read_text())
        if report.get('historical_scope') == 'Archived API sample':
            report['research_selected'] = str(prior.parent) in selected_paths
            prior.write_text(json.dumps(report, indent=2) + '\n')
    output = Path('data/processed/backfill')
    output.mkdir(parents=True, exist_ok=True)
    (output/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    return summaries


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--reviews', type=Path, default=Path('docs/backfill-price-reviews.json'))
    print(json.dumps(publish(cli.parse_args().reviews), indent=2))
