"""Explainable lexical similarity models for historical entity name review.

Scores are string-similarity signals, not probabilities of shared identity.
Transliteration and historical name changes must be supplied as reviewed aliases.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NameSimilarityScores:
    """Component metrics and their deterministic ensemble score."""

    jaro_winkler: float
    levenshtein: float
    damerau_levenshtein: float
    trigram_dice: float
    token_jaccard: float
    combined: float


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKC", value.casefold())
    return " ".join(re.findall(r"[^\W_]+", folded, flags=re.UNICODE))


def _jaro_winkler(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    radius = max(len(left), len(right)) // 2 - 1
    radius = max(0, radius)
    left_match = [False] * len(left)
    right_match = [False] * len(right)
    matches = 0
    for i, char in enumerate(left):
        for j in range(max(0, i - radius), min(i + radius + 1, len(right))):
            if not right_match[j] and char == right[j]:
                left_match[i] = right_match[j] = True
                matches += 1
                break
    if not matches:
        return 0.0
    left_ordered = [char for i, char in enumerate(left) if left_match[i]]
    right_ordered = [char for j, char in enumerate(right) if right_match[j]]
    transpositions = sum(a != b for a, b in zip(left_ordered, right_ordered)) / 2
    jaro = (
        matches / len(left)
        + matches / len(right)
        + (matches - transpositions) / matches
    ) / 3
    prefix = 0
    for a, b in zip(left, right):
        if a != b or prefix == 4:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1 - jaro)


def _edit_distance(left: str, right: str, *, allow_transposition: bool) -> int:
    rows, cols = len(left) + 1, len(right) + 1
    matrix = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        matrix[i][0] = i
    for j in range(cols):
        matrix[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )
            if (
                allow_transposition and i > 1 and j > 1
                and left[i - 1] == right[j - 2]
                and left[i - 2] == right[j - 1]
            ):
                matrix[i][j] = min(matrix[i][j], matrix[i - 2][j - 2] + 1)
    return matrix[-1][-1]


def _normalized_edit_similarity(left: str, right: str, *, damerau: bool) -> float:
    denominator = max(len(left), len(right))
    if denominator == 0:
        return 1.0
    distance = _edit_distance(left, right, allow_transposition=damerau)
    return 1.0 - distance / denominator


def _ngrams(value: str, n: int = 3) -> set[str]:
    if len(value) < n:
        return {value} if value else set()
    return {value[i:i + n] for i in range(len(value) - n + 1)}


def compare_names(left: str, right: str) -> NameSimilarityScores:
    """Compare two names with five complementary metrics and a fixed ensemble.

    Weights: Jaro-Winkler .65, Levenshtein .15, Damerau-Levenshtein .10,
    character-trigram Dice .07, and token Jaccard .03. The weights are a
    transparent starting heuristic, not learned/calibrated probabilities.
    """
    if not isinstance(left, str) or not isinstance(right, str):
        raise TypeError("name values must be strings")
    a, b = _normalize(left), _normalize(right)
    if not a or not b:
        values = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        return NameSimilarityScores(*values)
    if a == b:
        return NameSimilarityScores(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
    jw = _jaro_winkler(a, b)
    lev = _normalized_edit_similarity(a, b, damerau=False)
    dam = _normalized_edit_similarity(a, b, damerau=True)
    left_grams, right_grams = _ngrams(a), _ngrams(b)
    dice = (
        2 * len(left_grams & right_grams) / (len(left_grams) + len(right_grams))
        if left_grams or right_grams else 0.0
    )
    left_tokens, right_tokens = set(a.split()), set(b.split())
    jaccard = (
        len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        if left_tokens or right_tokens else 0.0
    )
    combined = 0.65 * jw + 0.15 * lev + 0.10 * dam + 0.07 * dice + 0.03 * jaccard
    return NameSimilarityScores(
        round(jw, 6), round(lev, 6), round(dam, 6),
        round(dice, 6), round(jaccard, 6), round(combined, 6),
    )
