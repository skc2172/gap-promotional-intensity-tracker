"""Date-bounded, append-only archive update using the existing evidence gates."""
import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from gap_tracker.backfill import discover, collect_candidates, eligible
from gap_tracker.backfill_publish import BASIS, representative, verified_review
from gap_tracker.categories import CATEGORIES, category_config
from gap_tracker.dashboard_data import ROOT, load_snapshots
from gap_tracker.metrics import write_metrics
from gap_tracker.parse_wayback import normalize_archived_api


def price_state(rows):
    return hashlib.sha256(json.dumps(sorted(
        (r['style_id'], r['product_id'], r['original_price'], r['current_price'])
        for r in rows)).encode()).hexdigest()


def update_archive(start, end, root=ROOT):
    if start > end or end > date.today():
        raise ValueError('Historical dates must be ordered and not in the future')
    run = root / 'data/raw/archive-updates' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    audit = {'start': start.isoformat(), 'end': end.isoformat(), 'discovery': [], 'attempts': [], 'added': 0}
    snapshots, errors = load_snapshots(root)
    audit['existing_snapshot_errors'] = errors
    historical = [s for s in snapshots if s['metrics']['source'] == 'gap_wayback']
    category_keys = {category_config(k)['category']: k for k in CATEGORIES}
    represented = {(category_keys[s['metrics']['category']], s['rows'][0]['provenance']['archive_timestamp']) for s in historical}
    months = {(category_keys[s['metrics']['category']], s['metrics']['snapshot_date'][:7]) for s in historical}
    states = {(category_keys[s['metrics']['category']], price_state(s['rows'])) for s in historical}
    review_file = root / 'docs/backfill-price-reviews.json'
    reviews = json.loads(review_file.read_text()) if review_file.exists() else []
    # Resolve existing review evidence relative to the repository, not process cwd.
    for review in reviews:
        for evidence in review.get('evidence', []):
            path = Path(evidence['file'])
            if not path.is_absolute():
                evidence['file'] = str(root / path)
    candidates = []
    for key in CATEGORIES:
        try:
            discovery = discover(key, start, end, run)
            audit['discovery'].append({'category': key, 'indices': discovery})
            attempts = collect_candidates(key, run, run / 'evidence', represented, start, end)
            for attempt in attempts:
                entry = {'category': key, **attempt}
                audit['attempts'].append(entry)
                if attempt['status'] != 'replay_verified':
                    continue
                try:
                    ts = attempt['actual_archive_timestamp']
                    if not start.strftime('%Y%m%d') <= ts[:8] <= end.strftime('%Y%m%d'):
                        raise ValueError('Capture outside requested period')
                    if (key, ts) in represented:
                        entry['status'] = 'already_represented'
                        continue
                    if not eligible(attempt['candidate']['original'], key):
                        raise ValueError('Unsupported archive request')
                    body = Path(attempt['raw_file']).read_bytes()
                    if hashlib.sha256(body).hexdigest() != attempt['sha256']:
                        raise ValueError('Raw archive hash mismatch')
                    review = verified_review(attempt, reviews)
                    if review is None:
                        entry['status'] = 'pending_price_basis_review'
                        continue
                    payload = json.loads(body)
                    rows = normalize_archived_api(payload, attempt, None, BASIS, category_config(key))
                    if any(r['original_price'] is None or r['current_price'] is None for r in rows):
                        raise ValueError('Incomplete archived price evidence')
                    if (key, rows[0]['snapshot_date'][:7]) in months or (key, price_state(rows)) in states:
                        entry['status'] = 'already_represented_month_or_price_state'
                        continue
                    candidates.append(dict(category_key=key, timestamp=ts, rows=rows, coverage=1,
                                           attempt=attempt, review=review, payload=payload, audit=entry))
                    entry['status'] = 'eligible_not_selected_monthly_representative'
                except (ValueError, KeyError, TypeError, OSError) as exc:
                    entry.update(status='rejected', reason=str(exc))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            audit['discovery'].append({'category': key, 'error': str(exc)})
    for candidate in representative(candidates):
        key, ts, rows = candidate['category_key'], candidate['timestamp'], candidate['rows']
        entry = candidate['audit']
        if (key, price_state(rows)) in states:
            entry['status'] = 'redundant_price_state'
            continue
        name = ts + '-' + key
        folder = root / 'data/processed/wayback' / name
        raw = root / 'data/raw/wayback' / name
        if folder.exists() or raw.exists():
            entry['status'] = 'existing_directory_preserved'
            continue
        folder.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Publish the complete processed directory only after metric validation.
            with tempfile.TemporaryDirectory(dir=run, prefix='staging-') as tmp:
                staging = Path(tmp) / name
                staging.mkdir()
                for row in rows:
                    row['provenance']['snapshot_id'] = name
                (staging / 'observations.json').write_text(json.dumps(rows, indent=2)+'\n')
                validation = dict(metrics_eligible=True, research_selected=True, historical_scope='Archived API sample',
                                  source_method='archived_category_api', category=category_config(key)['category'],
                                  raw_snapshot=raw.relative_to(root).as_posix(), archive_timestamp=ts,
                                  pages_collected=1, products_captured=len(rows), price_coverage=1,
                                  price_basis_review=json.loads(json.dumps(candidate['review']).replace(str(root) + '/', '')),
                                  selection='Append-only monthly representative; existing observations retained.',
                                  comparability='Single archived response, not a matched panel or full-assortment census; existing reviewed price basis applies.')
                (staging / 'validation.json').write_text(json.dumps(validation, indent=2)+'\n')
                write_metrics(staging / 'observations.json')
                raw.mkdir(parents=True)
                source = Path(candidate['attempt']['raw_file'])
                shutil.copyfile(source, raw / source.name)
                request = source.with_suffix(source.suffix + '.request.json')
                if request.exists():
                    shutil.copyfile(request, raw / request.name)
                (raw / 'archive-provenance.json').write_text(json.dumps(candidate['attempt'], indent=2)+'\n')
                staging.rename(folder)
            states.add((key, price_state(rows)))
            represented.add((key, ts))
            audit['added'] += 1
            entry['status'] = 'published'
        except (ValueError, KeyError, TypeError, OSError) as exc:
            entry.update(status='publication_failed', reason=str(exc))
    audit['incomplete'] = any('error' in d or any(i.get('status') != 200 or i.get('error') or i.get('usable') is False or i.get('potentially_truncated') for i in d.get('indices', [])) for d in audit['discovery'])
    (run / 'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    return {'added': audit['added'], 'incomplete': audit['incomplete']}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--start', type=date.fromisoformat, required=True)
    cli.add_argument('--end', type=date.fromisoformat, required=True)
    args = cli.parse_args()
    print(json.dumps(update_archive(args.start, args.end)))
