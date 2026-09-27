"""Offline Gap-specific adapter. No network calls or aggregate promo metrics."""
import argparse
import csv
import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs, urlparse

FIELDS = ["snapshot_date", "product_id", "style_id", "product_name", "category",
          "original_price", "current_price", "discount_pct", "is_discounted",
          "promo_text", "source", "source_url", "product_url", "currency",
          "raw_file", "raw_pointer", "source_percentage_off", "source_price_type",
          "promo_evidence", "price_basis", "provenance"]


def price(value):
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Unrecognized price: {value!r}") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"Invalid price: {value!r}")
    return result


def normalize(payload, manifest, raw_file="products.json"):
    if payload.get("locale") != "en_US":
        raise ValueError("Expected en_US; inspect market/currency before parsing")
    request = next(r for r in manifest["requests"] if r["file"] == raw_file)
    snapshot_date = datetime.fromisoformat(request["collected_at"]).date().isoformat()
    source_cid = parse_qs(urlparse(manifest["source_url"]).query).get("cid", [None])[0]
    expected_cid = manifest.get("category_id", source_cid)
    if not expected_cid or (source_cid and source_cid != expected_cid):
        raise ValueError("Missing or conflicting category identity")
    index = {}
    for pi, product in enumerate(payload["products"]):
        for ci, color in enumerate(product["styleColors"]):
            key = (product["styleId"], color["ccId"])
            if key in index:
                raise ValueError(f"Duplicate source identity: {key}")
            index[key] = (product, color, f"/products/{pi}/styleColors/{ci}")
    rows, seen = [], set()
    for category in payload["categories"]:
        if str(category["categoryId"]) != expected_cid:
            raise ValueError("Unexpected category")
        for ref in category["ccList"]:
            key = (ref["styleId"], ref["ccId"])
            if key in seen:
                continue  # A color may be listed under more than one subcategory.
            seen.add(key)
            if key not in index:
                raise ValueError(f"Listed product has no source record: {key}")
            product, color, pointer = index[key]
            original, current = price(color.get("regularPrice")), price(color.get("effectivePrice"))
            if original == 0 or (original is not None and current is not None and current > original):
                raise ValueError(f"Unexpected reference/current price relationship: {key}")
            known = original is not None and current is not None
            discount = (original - current) / original * 100 if known else None
            # Color-level flags only: do not project banners or style flags onto a color.
            flags = color.get("ccLevelMarketingFlags", [])
            promo = " | ".join(dict.fromkeys(f["content"] for f in flags if f.get("content"))) or None
            rows.append(dict(zip(FIELDS, [
                snapshot_date, color["ccId"], product["styleId"],
                color.get("styleName") or product.get("styleName"), manifest["category"],
                str(original) if original is not None else None,
                str(current) if current is not None else None,
                str(discount.quantize(Decimal("0.0001"))) if known else None,
                current < original if known else None, promo, "gap_current", manifest["source_url"],
                f"https://www.gap.com/browse/product.do?pid={color['ccId']}", "USD",
                raw_file, pointer,
                color.get("percentageOff") if color.get("percentageOff") != "" else None, color.get("priceType") or None,
                {"product_color_flags": color.get("ccLevelMarketingFlags"),
                 "product_color_badges": color.get("ccLevelBadges"),
                 "style_flags": product.get("styleMarketingFlags"),
                 "style_excluded_from_promotion": product.get("excludedFromPromotion")},
                "displayed_current_vs_retailer_reference",
                {"observed_at": request["collected_at"],
                 "retrieved_at": request["collected_at"],
                 "evidence_url": request.get("url"),
                 "evidence_sha256": request.get("sha256"),
                 "requested_target_period": None, "archive_timestamp": None,
                 "price_fields": {"original_price": "regularPrice", "current_price": "effectivePrice"}},
            ])))
    if not rows:
        raise ValueError("No listed products; refusing to produce an empty successful snapshot")
    return rows


def parse(folder, output_root=Path("data/processed")):
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Collection is incomplete")
    for request in manifest["requests"]:
        if hashlib.sha256((folder / request["file"]).read_bytes()).hexdigest() != request["sha256"]:
            raise ValueError(f"Raw evidence hash mismatch: {request['file']}")
    payload = json.loads((folder / "products.json").read_bytes())
    page_requests = [r for r in manifest["requests"] if r["file"].startswith("products")]
    if "expected_pages" in manifest and [r.get("page_number") for r in page_requests] != list(range(manifest["expected_pages"])):
        raise ValueError("Missing or unordered collected pages")
    rows, identities, duplicates, page_reports = [], {}, [], []
    for request in page_requests:
        page_payload = json.loads((folder / request["file"]).read_bytes())
        page_rows = normalize(page_payload, manifest, request["file"])
        page_reports.append({"file": request["file"], "listed_observations": len(page_rows),
                             "api_total_colors": page_payload.get("totalColors"),
                             "pagination": page_payload.get("pagination")})
        for row in page_rows:
            key = (row["style_id"], row["product_id"])
            if key in identities:
                first = identities[key]
                changed = [f for f in FIELDS if f not in {"raw_file", "raw_pointer", "provenance"}
                           and first[f] != row[f]]
                duplicates.append({"style_id": key[0], "product_id": key[1],
                                   "first_file": first["raw_file"], "duplicate_file": row["raw_file"],
                                   "changed_fields": changed})
                if changed:
                    raise ValueError(f"Conflicting observations across pages: {key}, {changed}")
                first["provenance"].setdefault("additional_occurrences", []).append({
                    "raw_file": row["raw_file"], "raw_pointer": row["raw_pointer"],
                    **row["provenance"]})
                continue
            identities[key] = row
            rows.append(row)
    for row in rows:
        row['provenance']['snapshot_id'] = folder.name
    output = output_root / folder.name
    output.mkdir(parents=True, exist_ok=True)
    with (output / "observations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        # Structured evidence is JSON in CSV cells, not Python dict repr.
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                          for k, v in row.items()} for row in rows)
    (output / "observations.json").write_text(json.dumps(rows, indent=2) + "\n")
    report = {
        "raw_snapshot": str(folder.resolve()), "parser_version": 4, "schema_version": 2,
        "observation_unit": "listed product-color ID; not unique style or size SKU",
        "products_captured": len(rows), "unique_styles": len({r['style_id'] for r in rows}),
        "category": manifest["category"],
        "category_id": manifest.get("category_id"),
        "department_id": manifest.get("department_id"),
        "price_coverage": sum(r["original_price"] is not None and r["current_price"] is not None for r in rows) / len(rows),
        "api_total_colors": payload.get("totalColors"), "pagination": payload.get("pagination"),
        "response_personalized": payload.get("metadata", {}).get("responsePersonalized"),
        "pages_collected": len(page_requests), "pages": page_reports,
        "duplicates_removed": len(duplicates), "duplicates": duplicates,
        "api_totals_by_page": [p["api_total_colors"] for p in page_reports],
        "api_total_changed_during_collection": len({p["api_total_colors"] for p in page_reports}) > 1,
        "api_total_minus_collected": int(payload["totalColors"]) - len(rows) if payload.get("totalColors") is not None else None,
        "missing": {field: {"count": sum(r[field] is None for r in rows),
                             "rate": sum(r[field] is None for r in rows) / len(rows)}
                    for field in ["product_name", "original_price", "current_price", "promo_text"]},
        "limitations": ["All reported pages collected; API total may differ from listed unique observations"
                        if "expected_pages" in manifest else "Legacy first-response snapshot",
                        "Additional swatch records excluded unless listed in categories[].ccList",
                        "Prices are advertised category prices, not verified checkout prices",
                        "Offer text is not applied to prices; missing flags do not prove no offer",
                        "USD derives from the fixed US collection context"],
    }
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return rows


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("snapshot", type=Path, help="Directory containing manifest.json and products.json")
    parse(cli.parse_args().snapshot)
