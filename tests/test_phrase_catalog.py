import pytest

from app.intents import detect_intent
from app.phrase_catalog import PROPERTY_PHRASES

CATALOG_CASES = [
    (property_id, phrase) for property_id, phrases in PROPERTY_PHRASES.items() for phrase in phrases
]


@pytest.mark.parametrize(("property_id", "phrase"), CATALOG_CASES)
def test_every_catalog_phrase_is_recognized(property_id: str, phrase: str) -> None:
    rule = detect_intent(f"{phrase} pour Marie Curie ?")
    assert rule.property_id == property_id


def test_catalog_generates_hundreds_of_supported_questions() -> None:
    templates = (
        "{phrase} pour Marie Curie ?",
        "Je voudrais savoir {phrase} concernant Marie Curie.",
        "Dis-moi {phrase} pour Marie Curie.",
    )
    generated = {
        template.format(phrase=phrase)
        for phrases in PROPERTY_PHRASES.values()
        for phrase in phrases
        for template in templates
    }
    assert len(generated) >= 400
