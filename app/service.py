from app.intents import IntentRule, detect_intent
from app.models import AnswerResponse, Evidence, Person
from app.wikidata import WikidataClient, format_claims, localized_value

PEOPLE = (
    Person(qid="Q7186", name="Marie Curie", description="Physicienne et chimiste franco-polonaise"),
    Person(qid="Q937", name="Albert Einstein", description="Physicien théoricien"),
    Person(qid="Q8023", name="Nelson Mandela", description="Président de l'Afrique du Sud"),
    Person(qid="Q76", name="Barack Obama", description="Président des États-Unis"),
    Person(qid="Q7259", name="Ada Lovelace", description="Mathématicienne britannique"),
    Person(qid="Q9036", name="Alan Turing", description="Mathématicien et cryptologue britannique"),
    Person(qid="Q317521", name="Simone Veil", description="Magistrate et femme d'État française"),
    Person(qid="Q392", name="Bob Marley", description="Auteur-compositeur-interprète jamaïcain"),
    Person(qid="Q762", name="Leonardo da Vinci", description="Artiste et savant italien"),
    Person(qid="Q5582", name="Vincent van Gogh", description="Peintre néerlandais"),
)


def build_answer(person_name: str, rule: IntentRule, values: list[str]) -> str:
    if not values:
        return (
            "Wikidata ne fournit pas de donnée pour "
            f"« {rule.property_label} » concernant {person_name}."
        )

    joined = ", ".join(values[:-1]) + (f" et {values[-1]}" if len(values) > 1 else values[0])
    templates = {
        "birth_date": f"{person_name} est né(e) le {joined}.",
        "birth_place": f"{person_name} est né(e) à {joined}.",
        "death_date": f"{person_name} est décédé(e) le {joined}.",
        "nationality": f"La ou les nationalités indiquées pour {person_name} sont : {joined}.",
        "occupation": f"{person_name} a exercé les professions suivantes : {joined}.",
        "education": f"{person_name} a fréquenté : {joined}.",
        "spouse": f"Le ou les conjoints indiqués pour {person_name} sont : {joined}.",
        "children": f"Les enfants indiqués pour {person_name} sont : {joined}.",
        "awards": f"Les distinctions indiquées pour {person_name} comprennent : {joined}.",
        "position": f"Les fonctions indiquées pour {person_name} comprennent : {joined}.",
    }
    return templates[rule.intent.value]


async def answer_question(
    client: WikidataClient,
    person_qid: str,
    question: str,
) -> AnswerResponse:
    rule = detect_intent(question)
    entity = await client.get_entity(person_qid)
    person = Person(
        qid=person_qid,
        name=localized_value(entity.get("labels", {})),
        description=localized_value(entity.get("descriptions", {})),
    )
    values = await format_claims(client, entity, rule.property_id)
    source_url = f"https://www.wikidata.org/wiki/{person_qid}"
    return AnswerResponse(
        person=person,
        question=question,
        intent=rule.intent,
        answer=build_answer(person.name, rule, values),
        evidence=Evidence(
            property_id=rule.property_id,
            property_label=rule.property_label,
            values=values,
            source_url=source_url,
        ),
    )
