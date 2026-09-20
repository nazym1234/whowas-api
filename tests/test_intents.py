import pytest

from app.intents import asks_for_count, detect_intent, extract_person_name
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


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Où est née Marie Curie ?", "Marie Curie"),
        ("Quelle était la profession d'Alan Turing ?", "Alan Turing"),
        ("Quels prix a reçu Nelson Mandela ?", "Nelson Mandela"),
        ("Qui sont les enfants de Barack Obama ?", "Barack Obama"),
    ],
)
def test_extract_person_name(question: str, expected: str) -> None:
    assert extract_person_name(question) == expected


def test_extract_person_from_count_question() -> None:
    question = "Combien de maris a eu Margot Robbie ?"
    assert detect_intent(question).intent == Intent.SPOUSE
    assert extract_person_name(question) == "Margot Robbie"
    assert asks_for_count(question)


def test_extract_person_and_property_from_free_question() -> None:
    question = "Quelle est la couleur des yeux de Margot Robbie ?"
    person = extract_person_name(question)
    assert person == "Margot Robbie"
    from app.intents import extract_property_query

    assert extract_property_query(question, person) == "couleur yeux"
