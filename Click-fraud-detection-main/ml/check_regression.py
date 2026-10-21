"""Compare a candidate model with a previously published metadata baseline."""
import argparse
import json
from pathlib import Path


def check(candidate: Path, baseline: Path) -> None:
    current = json.loads(candidate.read_text(encoding="utf-8"))["metrics"]
    previous = json.loads(baseline.read_text(encoding="utf-8"))["metrics"]
    if current["pr_auc"] < previous["pr_auc"]:
        raise SystemExit(f"PR-AUC regressed: {current['pr_auc']:.4f} < {previous['pr_auc']:.4f}")
    if current["cost"] > previous["cost"]:
        raise SystemExit(f"Cost increased: {current['cost']:.2f} > {previous['cost']:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("baseline", type=Path)
    args = parser.parse_args()
    check(args.candidate, args.baseline)
