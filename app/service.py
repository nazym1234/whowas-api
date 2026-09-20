from app.intents import IntentRule, asks_for_count, detect_intent, extract_person_name
from app.models import AnswerResponse, Evidence, Person
from app.wikidata import WikidataClient, format_claims, localized_value


def build_answer(
    person_name: str,
    rule: IntentRule,
    values: list[str],
    count_requested: bool = False,
) -> str:
    if not values:
        return (
            "Wikidata ne fournit pas de donnée pour "
            f"« {rule.property_label} » concernant {person_name}."
        )

    joined = ", ".join(values[:-1]) + (f" et {values[-1]}" if len(values) > 1 else values[0])
    if count_requested:
        labels = {
            "spouse": ("conjoint", "conjoints"),
            "children": ("enfant", "enfants"),
            "awards": ("distinction", "distinctions"),
            "position": ("fonction", "fonctions"),
            "occupation": ("profession", "professions"),
        }
        singular, plural = labels.get(rule.intent.value, ("résultat", "résultats"))
        label = singular if len(values) == 1 else plural
        return f"Wikidata recense {len(values)} {label} pour {person_name} : {joined}."
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
    question: str,
) -> AnswerResponse:
    rule = detect_intent(question)
    searched_name = extract_person_name(question)
    person_qid, entity = await client.search_person(searched_name)
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
        answer=build_answer(person.name, rule, values, asks_for_count(question)),
        evidence=Evidence(
            property_id=rule.property_id,
            property_label=rule.property_label,
            values=values,
            source_url=source_url,
        ),
    )
