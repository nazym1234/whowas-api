from app.models import Action
from app.query import analyze_question, extract_person_names


def test_age_question() -> None:
    plan = analyze_question("Quel âge a Margot Robbie ?")
    assert plan.action is Action.AGE
    assert plan.person_names == ["Margot Robbie"]


def test_age_question_accepts_a_lowercase_name() -> None:
    plan = analyze_question("Quel âge a billie eilish ?")
    assert plan.action is Action.AGE
    assert plan.person_names == ["billie eilish"]


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


def test_context_question_with_plain_pronoun() -> None:
    plan = analyze_question("Elle a combien d'enfants ?", has_context=True)
    assert plan.action is Action.COUNT
    assert plan.person_names == ["__context__"]


def test_context_question_with_plural_pronoun() -> None:
    plan = analyze_question("Ils ont quel âge ?", has_context=True)
    assert plan.action is Action.AGE
    assert plan.person_names == ["__context__"]


def test_elliptical_follow_up_uses_context() -> None:
    plan = analyze_question("Et en quelle année ?", has_context=True)
    assert plan.person_names == ["__context__"]


def test_plural_death_date_question() -> None:
    plan = analyze_question("Ils sont morts quand ?", has_context=True)
    assert plan.action is Action.LOOKUP
    assert plan.rule is not None
    assert plan.rule.property_id == "P570"


def test_plural_death_verification_question() -> None:
    plan = analyze_question("Ils sont morts ou pas ?", has_context=True)
    assert plan.action is Action.VERIFY
    assert plan.rule is not None
    assert plan.rule.property_id == "P570"


def test_extract_two_people() -> None:
    names = extract_person_names("Compare Marie Curie et Albert Einstein")
    assert names == ["Marie Curie", "Albert Einstein"]
