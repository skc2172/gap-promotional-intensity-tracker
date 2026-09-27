"""Run dated current snapshots, or resume a saved batch without recollecting it."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from gap_tracker.categories import CATEGORIES
from gap_tracker.collect import collect
from gap_tracker.parse import parse
from gap_tracker.metrics import write_metrics


def run(batch, categories):
    batch.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(batch.read_text()) if batch.exists() else {"categories": {}}
    for category in categories:
        entry = state["categories"].setdefault(category, {})
        try:
            if "raw_snapshot" not in entry:
                entry["raw_snapshot"] = str(collect(category=category))
                batch.write_text(json.dumps(state, indent=2) + "\n")
            raw = Path(entry["raw_snapshot"])
            parse(raw)
            output = Path("data/processed") / raw.name
            write_metrics(output / "observations.json")
            entry.update(status="complete", processed_snapshot=str(output))
            entry.pop("error", None)
        except Exception as exc:
            entry.update(status="failed", error=str(exc))
        batch.write_text(json.dumps(state, indent=2) + "\n")
    return state


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--category", choices=["all", *CATEGORIES], default="all")
    cli.add_argument("--batch", type=Path, help="Existing batch resumes saved successful collections")
    args = cli.parse_args()
    batch = args.batch or Path("data/processed/runs") / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    result = run(batch, list(CATEGORIES) if args.category == "all" else [args.category])
    print(f"Batch: {batch}")
    raise SystemExit(any(e["status"] != "complete" for e in result["categories"].values()))
