from __future__ import annotations

import sys
sys.path.insert(0, ".")

from backend import search


def test_rrf_ordering():
    weights = search.Weights(visual=0.35, irony=0.65)
    normalized = weights.normalized()
    assert 0.34 < normalized.visual < 0.36
    assert 0.64 < normalized.irony < 0.66
    print("RRF weight normalization OK")


def test_candidates_calculation():
    k = 20
    candidates_high_weight = search._candidates_per_space(0.65, k)
    candidates_low_weight = search._candidates_per_space(0.35, k)
    assert candidates_high_weight > candidates_low_weight
    print(f"Candidates calculation OK: high={candidates_high_weight}, low={candidates_low_weight}")


if __name__ == "__main__":
    test_rrf_ordering()
    test_candidates_calculation()
    print("All RRF validation tests passed")
