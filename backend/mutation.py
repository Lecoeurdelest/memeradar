from __future__ import annotations

import math


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(component * component for component in vector))
    if norm == 0.0:
        return [0.0] * len(vector)
    return [component / norm for component in vector]


def spherical_mean(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dimension = len(vectors[0])
    accumulator = [0.0] * dimension
    for vector in vectors:
        unit = l2_normalize(vector)
        for index in range(dimension):
            accumulator[index] += unit[index]
    count = len(vectors)
    mean = [component / count for component in accumulator]
    return l2_normalize(mean)


def cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    if similarity > 1.0:
        similarity = 1.0
    elif similarity < -1.0:
        similarity = -1.0
    return 1.0 - similarity


def l2_norm(vector: list[float]) -> float:
    return math.sqrt(sum(component * component for component in vector))
