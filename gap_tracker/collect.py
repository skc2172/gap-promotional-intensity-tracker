"""Collect all reported public category pages; never retry blocks."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from gap_tracker.categories import CATEGORIES, category_config

PAGE_URL = "https://www.gap.com/browse/women/jeans?cid=5664"
API_URL = "https://api.gap.com/v2/catalog_search_products/v2/category_products"
# Identified in Gap's public category JS, with anonymous client/session defaults.
PARAMS = dict(pageSize="200", pageNumber="0", cid="5664", vendor="constructorio",
              client_id="0", session_id="0", includeMarketingFlagsDetails="true",
              enableDynamicFacets="true", enableDynamicPhoto="true", brand="gap",
              locale="en_US", market="us", department="136")
HEADERS = {"x-client-application-name": "Browse", "X-Customer-Segment": "non-cardholder"}


def collect(root=Path("data/raw"), category="women-jeans"):
    config = category_config(category)
    params = {**PARAMS, "cid": config["category_id"], "department": config["department_id"]}
    started = datetime.now(timezone.utc)
    folder = root / (started.strftime("%Y%m%dT%H%M%S%fZ") + "-" + category)
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 1, "source": "gap_current", **config,
                "collection_scope": "all reported pages, pageSize=200", "started_at": started.isoformat(),
                "requests": [], "status": "incomplete"}
    try:
        pending = [
            ("page.html", config["source_url"], None, None),
            ("products.json", API_URL, params, HEADERS),
        ]
        expected_pages = None
        for filename, url, params, headers in pending:
            response = requests.get(url, params=params, headers=headers, timeout=(10, 45))
            body = response.content  # Original body after HTTP transport decompression.
            (folder / filename).write_bytes(body)
            manifest["requests"].append({
                "file": filename, "url": response.url,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "status_code": response.status_code,
                "request_headers": dict(response.request.headers),
                "response_headers": {k: v for k, v in response.headers.items()
                                     if k.lower() != "set-cookie"},
                "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
            })
            response.raise_for_status()  # Preserve errors, then stop. No bypasses.
            if filename == "page.html" and (
                "plp-product-list" not in response.text
                or "plp-category-products-endpoint\\\":true" not in response.text
            ):
                raise ValueError("Category shell/endpoint flag changed; inspect saved HTML before proceeding")
            if filename.startswith("products"):
                payload = response.json()
                if not payload.get("products") or not payload.get("categories"):
                    raise ValueError("No product/category data; inspect saved response")
                pagination = payload.get("pagination", {})
                page = int(params["pageNumber"])
                count = int(pagination["pageNumberTotal"])
                if int(pagination["currentPage"]) != page or not 1 <= count <= 100:
                    raise ValueError("Unexpected pagination metadata; inspect raw response")
                if expected_pages is None:
                    expected_pages = count
                    manifest["expected_pages"] = count
                    pending.extend((f"products-page-{n}.json", API_URL,
                                    {**params, "pageNumber": str(n)}, HEADERS)
                                   for n in range(1, count))
                elif count != expected_pages:
                    raise ValueError("Page count changed during collection; snapshot incomplete")
                manifest["requests"][-1]["page_number"] = page
        manifest["status"] = "complete"
    except Exception as exc:
        manifest["error"] = str(exc)
        raise
    finally:
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(folder)
    return folder


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--category", choices=CATEGORIES, default="women-jeans")
    collect(category=cli.parse_args().category)
