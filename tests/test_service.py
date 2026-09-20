from app.intents import RULES
from app.service import build_answer


def test_build_birth_place_answer() -> None:
    rule = next(rule for rule in RULES if rule.property_id == "P19")
    assert build_answer("Marie Curie", rule, ["Varsovie"]) == "Marie Curie est né(e) à Varsovie."


def test_build_missing_answer() -> None:
    rule = next(rule for rule in RULES if rule.property_id == "P26")
    answer = build_answer("Ada Lovelace", rule, [])
    assert "ne fournit pas" in answer


def test_build_count_answer() -> None:
    rule = next(rule for rule in RULES if rule.property_id == "P26")
    answer = build_answer("Margot Robbie", rule, ["Tom Ackerley"], count_requested=True)
    assert "1 conjoint" in answer
    assert "Tom Ackerley" in answer


def test_build_generic_answer() -> None:
    from app.intents import IntentRule
    from app.models import Intent

    rule = IntentRule(Intent.GENERIC, "P1340", "couleur des yeux", ())
    answer = build_answer("David Bowie", rule, ["bleu"])
    assert "couleur des yeux" in answer
    assert "bleu" in answer
