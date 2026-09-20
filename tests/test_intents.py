import pytest

from app.intents import detect_intent
from app.models import Intent


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Quand est née cette personne ?", Intent.BIRTH_DATE),
        ("Où est né cet homme ?", Intent.BIRTH_PLACE),
        ("Quand est-elle décédée ?", Intent.DEATH_DATE),
        ("Quelle est sa nationalité ?", Intent.NATIONALITY),
        ("Quelle était sa profession ?", Intent.OCCUPATION),
        ("Dans quelle université a-t-elle étudié ?", Intent.EDUCATION),
        ("Avec qui était-elle mariée ?", Intent.SPOUSE),
        ("Qui sont ses enfants ?", Intent.CHILDREN),
        ("Quels prix a-t-elle reçus ?", Intent.AWARDS),
        ("Quelles fonctions a-t-elle occupées ?", Intent.POSITION),
    ],
)
def test_detect_ten_intents(question: str, expected: Intent) -> None:
    assert detect_intent(question).intent == expected


def test_unknown_question() -> None:
    with pytest.raises(ValueError):
        detect_intent("Raconte-moi quelque chose")
