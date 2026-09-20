from app.models import Action
from app.query import analyze_question, extract_person_names


def test_age_question() -> None:
    plan = analyze_question("Quel âge a Margot Robbie ?")
    assert plan.action is Action.AGE
    assert plan.person_names == ["Margot Robbie"]


def test_comparison_question() -> None:
    plan = analyze_question("Qui est le plus âgé entre Messi et Ronaldo ?")
    assert plan.action is Action.COMPARE
    assert plan.person_names == ["Messi", "Ronaldo"]


def test_count_question() -> None:
    plan = analyze_question("Combien d'enfants a Barack Obama ?")
    assert plan.action is Action.COUNT


def test_context_question() -> None:
    plan = analyze_question("Où est-elle née ?", has_context=True)
    assert plan.person_names == ["__context__"]


def test_extract_two_people() -> None:
    names = extract_person_names("Compare Marie Curie et Albert Einstein")
    assert names == ["Marie Curie", "Albert Einstein"]
