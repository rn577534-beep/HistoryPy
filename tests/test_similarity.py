import pytest

from historypy import NameSimilarityScores, compare_names


def test_exact_names_score_one_for_every_metric():
    scores = compare_names("Jeanne d'Arc", "Jeanne d'Arc")
    assert isinstance(scores, NameSimilarityScores)
    assert scores.combined == 1.0
    assert scores.jaro_winkler == 1.0
    assert scores.levenshtein == 1.0
    assert scores.damerau_levenshtein == 1.0
    assert scores.trigram_dice == 1.0
    assert scores.token_jaccard == 1.0


def test_similarity_is_case_and_unicode_normalization_aware():
    assert compare_names("SOCIÉTÉ DES NATIONS", "Société des Nations").combined == 1.0


def test_damerau_levenshtein_rewards_adjacent_transposition():
    transposed = compare_names("hte", "the")
    assert transposed.damerau_levenshtein == pytest.approx(2 / 3)
    assert transposed.levenshtein == pytest.approx(1 / 3)
    assert transposed.levenshtein < transposed.damerau_levenshtein


def test_fuzzy_name_ensemble_detects_near_spelling_without_claiming_identity():
    scores = compare_names("Alexandre", "Alexander")
    assert 0.0 < scores.combined < 1.0
    assert scores.jaro_winkler > scores.levenshtein
    assert compare_names("Alexandre", "Aristotle").combined < scores.combined


def test_empty_and_invalid_inputs_are_handled():
    assert compare_names("", "Alexander").combined == 0.0
    with pytest.raises(TypeError, match="strings"):
        compare_names(None, "Alexander")
