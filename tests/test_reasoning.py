from datetime import date

from app.models import Person
from app.service import _verification_answer, _years_between


def test_years_between_accounts_for_birthday() -> None:
    assert _years_between(date(2000, 6, 10), date(2025, 6, 9)) == 24
    assert _years_between(date(2000, 6, 10), date(2025, 6, 10)) == 25


def test_verification_with_demonym() -> None:
    person = Person(qid="Q1", name="Exemple", description="Description")
    answer = _verification_answer(person, "Est-elle australienne ?", ["Australie"])
    assert answer.startswith("Oui")
