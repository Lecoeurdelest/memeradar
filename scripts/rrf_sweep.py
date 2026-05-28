from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.parse
from itertools import combinations

WEIGHT_PAIRS = [
    (1.0, 0.0),
    (0.75, 0.25),
    (0.5, 0.5),
    (0.25, 0.75),
    (0.0, 1.0),
]

MIN_RESULTS_PER_STEP = 5


def _fetch(base_url: str, query: str, visual: float, irony: float, k: int) -> list[str]:
    params = urllib.parse.urlencode({
        "q": query,
        "k": k,
        "visual_weight": visual,
        "irony_weight": irony,
    })
    with urllib.request.urlopen(f"{base_url}/search?{params}", timeout=30) as r:
        data = json.loads(r.read())
    return [hit["id"] for hit in data.get("results", [])]


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def run(base_url: str, query: str, k: int) -> int:
    print(f"Query: {query!r}  k={k}  base={base_url}\n")

    result_sets: dict[tuple[float, float], list[str]] = {}
    for v, i in WEIGHT_PAIRS:
        ids = _fetch(base_url, query, v, i, k)
        result_sets[(v, i)] = ids
        print(f"  visual={v:.2f} irony={i:.2f}  -> {len(ids)} results  top={ids[:3]}")

    pairs = list(combinations(WEIGHT_PAIRS, 2))
    matrix: dict[str, float] = {}
    print("\nJaccard similarity matrix:")
    header = "              " + "".join(f"  v{v:.2f}/i{ir:.2f}" for v, ir in WEIGHT_PAIRS)
    print(header)
    for a in WEIGHT_PAIRS:
        row = f"v{a[0]:.2f}/i{a[1]:.2f}  "
        for b in WEIGHT_PAIRS:
            j = _jaccard(result_sets[a], result_sets[b])
            key = f"{a[0]}/{a[1]}__vs__{b[0]}/{b[1]}"
            matrix[key] = round(j, 4)
            row += f"  {j:.4f}   "
        print(row)

    a, e = WEIGHT_PAIRS[0], WEIGHT_PAIRS[-1]
    top1_a = result_sets[a][0] if result_sets[a] else None
    top1_e = result_sets[e][0] if result_sets[e] else None
    rank_shift_ok = top1_a is not None and top1_e is not None and top1_a != top1_e

    jaccard_chain = [_jaccard(result_sets[a], result_sets[b]) for b in WEIGHT_PAIRS[1:]]
    monotonic_ok = all(earlier > later for earlier, later in zip(jaccard_chain, jaccard_chain[1:]))

    min_required = min(MIN_RESULTS_PER_STEP, k)
    empty_steps = [f"v{v:.2f}/i{i:.2f}" for v, i in WEIGHT_PAIRS if len(result_sets[(v, i)]) < min_required]
    no_empty_ok = not empty_steps

    extreme_jaccard = _jaccard(result_sets[a], result_sets[e])
    passed = rank_shift_ok and monotonic_ok and no_empty_ok

    report = {
        "query": query,
        "k": k,
        "weight_pairs": [{"visual": v, "irony": i, "result_ids": result_sets[(v, i)]} for v, i in WEIGHT_PAIRS],
        "jaccard_matrix": matrix,
        "extreme_jaccard": extreme_jaccard,
        "rank_shift_ok": rank_shift_ok,
        "monotonic_ok": monotonic_ok,
        "monotonic_chain": [round(x, 4) for x in jaccard_chain],
        "no_empty_ok": no_empty_ok,
        "passed": passed,
    }
    out_path = "data/rrf_sweep_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written -> {out_path}")

    print("\nAssertions:")
    print(f"  rank shift (top1 A != top1 E): {'PASS' if rank_shift_ok else 'FAIL'}  ({top1_a} vs {top1_e})")
    print(f"  monotonic Jaccard chain J(A,B)>J(A,C)>J(A,D)>J(A,E): {'PASS' if monotonic_ok else 'FAIL'}  {[round(x, 4) for x in jaccard_chain]}")
    print(f"  no empty pages (>= {min_required}/step): {'PASS' if no_empty_ok else 'FAIL'}  {('all ok' if no_empty_ok else empty_steps)}")

    if not passed:
        print("\nFAIL: one or more RRF sweep assertions did not hold.")
        return 1

    print("\nPASS: rank shift observable, transition monotonic, no empty pages.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--query", default="person reacting with shock or disbelief")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    sys.exit(run(args.url, args.query, args.k))
