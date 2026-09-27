"""Source-independent snapshot metrics from normalized JSON; no collection calls."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from statistics import median

BANDS = ('0%', '>0–<20%', '20–<30%', '30–<40%', '40–<50%', '≥50%')
CONTEXT = ('snapshot_date', 'source', 'source_url', 'category', 'currency')


def markdown(original, current):
    """Exact rational arithmetic; missing prices remain unknown."""
    values = []
    for value in (original, current):
        if value is None or value == '':
            values.append(None)
            continue
        try:
            number = Fraction(str(value))
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f'Invalid price: {value!r}') from exc
        if number < 0:
            raise ValueError('Prices must be nonnegative')
        values.append(number)
    original, current = values
    if original == 0:
        raise ValueError('Original price must be positive')
    if original is None or current is None:
        return None
    if current > original:
        raise ValueError('Current price exceeds original price')
    return 100 * (original - current) / original


def number(value):
    return None if value is None else round(float(value), 6)


def calculate(rows):
    if not rows:
        raise ValueError('An empty dataset is not a valid snapshot')
    context = {key: rows[0][key] for key in CONTEXT}
    seen, styles, discounts = set(), set(), []
    bands = dict.fromkeys(BANDS, 0)
    for row in rows:
        if row.get('source') == 'gap_wayback' and row.get('price_basis') != 'displayed_current_vs_retailer_reference':
            raise ValueError('Historical display-price comparability has not been verified')
        if any(row[key] != context[key] for key in CONTEXT):
            raise ValueError('Expected one snapshot, source, category, and currency')
        identity = (row['style_id'], row['product_id'])
        if not all(identity) or identity in seen:
            raise ValueError('Missing or duplicate product-color identity')
        seen.add(identity)
        styles.add(row['style_id'])
        discount = markdown(row['original_price'], row['current_price'])
        if discount is None:
            continue
        discounts.append(discount)
        band = (BANDS[0] if discount == 0 else BANDS[1] if discount < 20 else
                BANDS[2] if discount < 30 else BANDS[3] if discount < 40 else
                BANDS[4] if discount < 50 else BANDS[5])
        bands[band] += 1
    total = len(rows)
    discounted = [d for d in discounts if d > 0]
    at_least_30 = sum(d >= 30 for d in discounts)
    return {
        'metrics_version': 1, **context,
        'observation_unit': 'product-color (style_id, product_id)',
        'total_observations': total, 'unique_styles_observed': len(styles),
        'price_eligible_observations': len(discounts),
        'missing_price_observations': total - len(discounts),
        'full_price_observations': bands['0%'],
        'discounted_observations': len(discounted),
        'share_discounted': number(Fraction(len(discounted), total)),
        'median_discount_pct_among_discounted': number(median(discounted)) if discounted else None,
        'mean_discount_pct_among_discounted': number(sum(discounted) / len(discounted)) if discounted else None,
        'observations_discounted_at_least_30_pct': at_least_30,
        'share_discounted_at_least_30_pct': number(Fraction(at_least_30, total)),
        'discount_bands': {band: {'count': count, 'share_all_observations': number(Fraction(count, total))}
                           for band, count in bands.items()},
        'definitions': {
            'markdown': '100 * (original_price - current_price) / original_price',
            'shares': 'Fractions 0–1; denominator is all product-color observations, including missing-price rows.',
            'missing_prices': 'Unknown, not full-price. With missing prices, shares are confirmed discounted counts / all observations (lower bounds). Bands exclude unknowns.',
            'averages': 'Equal weight per discounted product-color observation; null if none are discounted.',
            'rounding': 'Exact rational arithmetic for classification and aggregation; output rounded to six decimal places.',
            'promotions': 'promo_text, stored discount_pct, and stored is_discounted are not used.',
        },
    }


def write_metrics(observations):
    body = observations.read_bytes()
    result = calculate(json.loads(body))
    result['input'] = {'file': observations.name, 'sha256': hashlib.sha256(body).hexdigest(),
                       'snapshot_id': observations.parent.name}
    output = observations.with_name('metrics.json')
    if output == observations:
        raise ValueError('Input must not be named metrics.json')
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return output


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('observations', type=Path)
    print(write_metrics(cli.parse_args().observations))
