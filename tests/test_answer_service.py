import asyncio

from app.models import Action, PersonCandidate
from app.service import answer_group_question, answer_question


def time_claim(value: str) -> list[dict[str, object]]:
    return [
        {
            "rank": "normal",
            "mainsnak": {"datavalue": {"type": "time", "value": {"time": value}}},
        }
    ]


def entity_claim(qid: str) -> list[dict[str, object]]:
    return [
        {
            "rank": "normal",
            "mainsnak": {"datavalue": {"type": "wikibase-entityid", "value": {"id": qid}}},
        }
    ]


def make_entity(qid: str, name: str, birth: str, death: str | None = None):
    claims = {
        "P31": entity_claim("Q5"),
        "P569": time_claim(birth),
        "P27": entity_claim("Q408"),
        "P1340": entity_claim("Q17122834"),
        "P39": [
            {
                "rank": "normal",
                "mainsnak": {"datavalue": {"type": "wikibase-entityid", "value": {"id": "Q100"}}},
                "qualifiers": {
                    "P580": [
                        {"datavalue": {"type": "time", "value": {"time": "+2000-01-01T00:00:00Z"}}}
                    ],
                    "P582": [
                        {"datavalue": {"type": "time", "value": {"time": "+2004-01-01T00:00:00Z"}}}
                    ],
                },
            }
        ],
    }
    if death:
        claims["P570"] = time_claim(death)
    return {
        "id": qid,
        "labels": {"fr": {"value": name}},
        "descriptions": {"fr": {"value": f"Description de {name}"}},
        "claims": claims,
        "sitelinks": {"frwiki": {"title": name}},
    }


class FakeClient:
    def __init__(self) -> None:
        self.entities = {
            "Q1": make_entity(
                "Q1", "Marie Curie", "+1867-11-07T00:00:00Z", "+1934-07-04T00:00:00Z"
            ),
            "Q2": make_entity(
                "Q2", "Albert Einstein", "+1879-03-14T00:00:00Z", "+1955-04-18T00:00:00Z"
            ),
        }
        self.entities["Q1"]["claims"]["P40"] = entity_claim("Q2")

    async def search_people(self, name: str):
        qid = "Q2" if "Einstein" in name else "Q1"
        entity = self.entities[qid]
        return [
            PersonCandidate(
                qid=qid,
                name=entity["labels"]["fr"]["value"],
                description=entity["descriptions"]["fr"]["value"],
                score=1.0,
            )
        ]

    async def search_person(self, name: str):
        qid = "Q2" if "Einstein" in name else "Q1"
        return qid, self.entities[qid]

    async def get_entity(self, qid: str):
        return self.entities[qid]

    async def get_labels(self, qids: set[str], language: str = "fr"):
        labels = {
            "Q2": "Albert Einstein",
            "Q408": "Australie",
            "Q17122834": "bleu",
            "Q100": "présidente",
        }
        return {qid: labels[qid] for qid in qids}

    async def search_properties(self, query: str):
        if query == "couleur yeux":
            return [("P1340", "couleur des yeux")]
        return []

    async def get_wikipedia_summary(self, entity):
        return f"Résumé encyclopédique de {entity['labels']['fr']['value']}"


def run_answer(question: str, **kwargs):
    return asyncio.run(answer_question(FakeClient(), question, **kwargs))


def test_age_answer() -> None:
    result = run_answer("Quel âge avait Marie Curie ?")
    assert result.action is Action.AGE
    assert "66 ans" in result.answer


def test_lifespan_answer() -> None:
    result = run_answer("Combien de temps Marie Curie a-t-elle vécu ?")
    assert result.action is Action.DURATION
    assert "66 ans" in result.answer


def test_qualified_duration_answer() -> None:
    result = run_answer("Combien de temps Marie Curie a-t-elle été présidente ?")
    assert result.action is Action.DURATION
    assert "4 an(s)" in result.answer
    assert result.evidence.details[0].start_date == "1 janvier 2000"


def test_age_comparison() -> None:
    result = run_answer("Qui est le plus âgé entre Marie Curie et Albert Einstein ?")
    assert result.action is Action.COMPARE
    assert "Marie Curie est la personne la plus âgée" in result.answer
    assert len(result.related_people) == 1


def test_dynamic_property_answer() -> None:
    result = run_answer("Quelle est la couleur des yeux de Marie Curie ?")
    assert result.evidence.property_id == "P1340"
    assert "bleu" in result.answer


def test_missing_dynamic_property_returns_person_source() -> None:
    result = run_answer("Quel est le signe astrologique de Marie Curie ?")
    assert result.evidence.resolution == "no_data"
    assert result.evidence.source_url.endswith("/Q1")
    assert "consulter directement sa fiche Wikidata" in result.answer


def test_missing_known_value_returns_person_source() -> None:
    result = run_answer("Qui sont ses enfants ?", context_qid="Q2")
    assert result.evidence.resolution == "no_data"
    assert result.evidence.source_url.endswith("/Q2")


def test_summary_answer() -> None:
    result = run_answer("Qui est Marie Curie ?")
    assert "Résumé encyclopédique" in result.answer
    assert result.evidence.resolution == "wikipedia_summary"


def test_context_qid_answer() -> None:
    result = run_answer("Où est-elle née ?", context_qid="Q1")
    assert result.person.qid == "Q1"


def test_context_qid_birth_place_with_inverted_word_order() -> None:
    result = run_answer("Elle est née où ?", context_qid="Q1")
    assert result.person.qid == "Q1"
    assert result.evidence.property_id == "P19"
    assert result.evidence.source_url.endswith("/Q1")


def test_context_qid_with_plain_pronoun() -> None:
    result = run_answer("Elle a combien d'enfants ?", context_qid="Q1")
    assert result.person.qid == "Q1"
    assert result.action is Action.COUNT
    assert [person.qid for person in result.related_people] == ["Q2"]


def test_group_context_answers_for_every_mentioned_person() -> None:
    result = asyncio.run(answer_group_question(FakeClient(), "Ils ont quel âge ?", ["Q1", "Q2"]))
    assert result.evidence.resolution == "conversation_group"
    assert "Marie Curie" in result.answer
    assert "Albert Einstein" in result.answer


def test_group_context_accepts_leading_and_plural_age() -> None:
    result = asyncio.run(
        answer_group_question(FakeClient(), "Et ils ont quels âges ?", ["Q1", "Q2"])
    )
    assert result.evidence.property_id == "P569"
    assert "Marie Curie" in result.answer
    assert "Albert Einstein" in result.answer


def test_group_context_handles_plural_birth_date() -> None:
    result = asyncio.run(answer_group_question(FakeClient(), "Ils sont nés quand ?", ["Q1", "Q2"]))
    assert result.evidence.property_id == "P569"
    assert "7 novembre 1867" in result.answer
    assert "14 mars 1879" in result.answer


def test_group_context_handles_plural_death_date() -> None:
    result = asyncio.run(
        answer_group_question(FakeClient(), "Ils sont morts quand ?", ["Q1", "Q2"])
    )
    assert "4 juillet 1934" in result.answer
    assert "18 avril 1955" in result.answer


def test_group_context_handles_plural_death_verification() -> None:
    result = asyncio.run(
        answer_group_question(FakeClient(), "Ils sont morts ou pas ?", ["Q1", "Q2"])
    )
    assert "Oui, Marie Curie est décédé(e)" in result.answer
    assert "Oui, Albert Einstein est décédé(e)" in result.answer


def test_verification_answer() -> None:
    result = run_answer("Marie Curie est-elle australienne ?")
    assert result.action is Action.VERIFY
    assert result.answer.startswith("Oui")
