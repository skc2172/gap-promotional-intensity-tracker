"""Read-only presentation adapters; refresh delegates to the existing pipeline."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEASURES = {
    'Discount Breadth': 'share_discounted',
    'Median Discount Depth': 'median_discount_pct_among_discounted',
    'Deep-Discount Share ≥30%': 'share_discounted_at_least_30_pct',
}


def load_snapshots(root=ROOT):
    snapshots, errors = [], []
    for path in sorted((root / 'data/processed').rglob('metrics.json')):
        if 'schema-v1' in path.parts:
            continue
        try:
            metrics = json.loads(path.read_text())
            body = path.with_name('observations.json').read_bytes()
            if hashlib.sha256(body).hexdigest() != metrics['input']['sha256']:
                raise ValueError('Observation hash does not match saved metrics')
            rows = json.loads(body)
            validation = json.loads(path.with_name('validation.json').read_text())
            if validation.get('research_selected') is False:
                continue
            historical = metrics['source'] == 'gap_wayback'
            if historical and not validation.get('metrics_eligible'):
                raise ValueError('Historical metrics not validated')
            # Snapshot directories mirror data/processed under data/raw. Resolve
            # relative metadata against the supplied repository, never the cwd.
            raw = root / 'data/raw' / path.parent.relative_to(root / 'data/processed')
            if historical and validation.get('raw_snapshot'):
                saved_raw = Path(validation['raw_snapshot'])
                if not saved_raw.is_absolute():
                    raw = root / saved_raw
                # Legacy absolute metadata uses the mirrored repository location.
            manifest = json.loads((raw / 'manifest.json').read_text()) if not historical else {}
            scope = (validation.get('historical_scope', 'Archive alternative') if historical else
                     'All reported pages' if 'expected_pages' in manifest else 'First page only')
            snapshots.append(dict(id=str(path.parent.relative_to(root / 'data/processed')),
                                  folder=path.parent, raw=raw, metrics=metrics, rows=rows,
                                  validation=validation, scope=scope,
                                  observed_at=rows[0]['provenance']['observed_at']))
        except (ValueError, KeyError, OSError, IndexError) as exc:
            errors.append(f'{path.parent.name}: {exc}')
    return sorted(snapshots, key=lambda s: s['observed_at']), errors


def metric_value(metrics, label):
    value = metrics[MEASURES[label]]
    return None if value is None else value * (1 if label == 'Median Discount Depth' else 100)


def evidence_rows(snapshot):
    """Enrich color from hash-verified saved raw ccName, without changing schema."""
    payloads, result = {}, []
    for row in snapshot['rows']:
        color = None
        try:
            path = snapshot['raw'] / row['raw_file']
            expected = row['provenance']['evidence_sha256']
            key = (path, expected)
            if key not in payloads:
                body = path.read_bytes()
                payloads[key] = json.loads(body) if hashlib.sha256(body).hexdigest() == expected else None
            node = payloads[key]
            for part in row['raw_pointer'].strip('/').split('/'):
                node = node[int(part)] if isinstance(node, list) else node[part]
            color = node.get('ccName')
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            pass  # Missing evidence stays unknown, never guessed from a name or image.
        result.append({'Product': row['product_name'], 'Color': color,
                       'Style ID': row['style_id'], 'Product-color ID': row['product_id'],
                       'Reference price': float(row['original_price']) if row['original_price'] is not None else None,
                       'Current price': float(row['current_price']) if row['current_price'] is not None else None,
                       'Discount %': float(row['discount_pct']) if row['discount_pct'] is not None else None,
                       'Promotional messaging': row['promo_text'], 'Product URL': row['product_url'],
                       'Raw file': row['raw_file'], 'Raw pointer': row['raw_pointer']})
    return result


def refresh_current(root=ROOT):
    """Explicit action only; new batch path on every call, failures remain visible."""
    batch = root / 'data/processed/runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-dashboard.json')
    process = subprocess.run([sys.executable, '-m', 'gap_tracker.current', '--batch', str(batch)],
                             cwd=root, capture_output=True, text=True)
    state = json.loads(batch.read_text()) if batch.exists() else {}
    return {'batch': str(batch), 'returncode': process.returncode,
            'categories': state.get('categories', {}),
            'error': process.stderr[-2000:] if process.returncode else None}


def daily_snapshots(snapshots):
    """Presentation selection only: latest per UTC day/category/coverage regime."""
    daily = {}
    for snapshot in sorted(snapshots, key=lambda s: s['observed_at']):
        key = (snapshot['metrics']['snapshot_date'], snapshot['metrics']['category'], snapshot['scope'])
        daily[key] = snapshot
    return list(daily.values())


def readable_time(value):
    return datetime.fromisoformat(value).strftime('%b %d, %Y · %H:%M UTC')
