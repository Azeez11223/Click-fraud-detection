"""Local Population Stability Index report for a feature CSV."""
import argparse
import json

import numpy as np
import pandas as pd


def psi(reference, current, bins=10):
    edges = np.unique(np.quantile(reference.dropna(), np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    expected = np.histogram(reference.dropna(), bins=edges)[0] / max(1, reference.notna().sum())
    actual = np.histogram(current.dropna(), bins=edges)[0] / max(1, current.notna().sum())
    expected, actual = np.clip(expected, 1e-6, None), np.clip(actual, 1e-6, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("reference")
    parser.add_argument("current")
    args = parser.parse_args()
    ref, cur = pd.read_csv(args.reference), pd.read_csv(args.current)
    print(json.dumps({c: psi(ref[c], cur[c]) for c in ref.select_dtypes(include="number") if c in cur}, indent=2))
