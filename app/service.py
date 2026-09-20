from urllib.parse import quote

from app.intents import (
    IntentRule,
    asks_for_count,
    detect_intent,
    extract_person_name,
    extract_property_query,
)
from app.models import AnswerResponse, Evidence, Intent, Person
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
        "summary": f"{person_name} : {joined}.",
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
        "family": f"Pour {rule.property_label}, Wikidata indique pour {person_name} : {joined}.",
        "employer": f"Les employeurs indiqués pour {person_name} sont : {joined}.",
        "residence": f"Les lieux de résidence indiqués pour {person_name} sont : {joined}.",
        "religion": f"La religion indiquée pour {person_name} est : {joined}.",
        "political_party": f"Le parti politique indiqué pour {person_name} est : {joined}.",
        "languages": f"Les langues indiquées pour {person_name} sont : {joined}.",
        "notable_work": f"Les œuvres principales indiquées pour {person_name} sont : {joined}.",
        "field": f"Les domaines indiqués pour {person_name} sont : {joined}.",
        "genre": f"Les genres indiqués pour {person_name} sont : {joined}.",
        "instrument": f"Les instruments indiqués pour {person_name} sont : {joined}.",
        "height": f"La taille indiquée pour {person_name} est : {joined}.",
        "cause_of_death": f"La cause de décès indiquée pour {person_name} est : {joined}.",
        "burial_place": f"Le lieu d'inhumation indiqué pour {person_name} est : {joined}.",
        "website": f"Le site officiel indiqué pour {person_name} est : {joined}.",
        "generic": f"Pour « {rule.property_label} », Wikidata indique pour {person_name} : {joined}.",
    }
    return templates[rule.intent.value]


async def answer_question(
    client: WikidataClient,
    question: str,
) -> AnswerResponse:
    try:
        rule = detect_intent(question)
        resolution = "rule"
    except ValueError:
        rule = None
        resolution = "dynamic_property"
    searched_name = extract_person_name(question)
    person_qid, entity = await client.search_person(searched_name)
    person = Person(
        qid=person_qid,
        name=localized_value(entity.get("labels", {})),
        description=localized_value(entity.get("descriptions", {})),
    )
    if rule is None:
        property_query = extract_property_query(question, searched_name)
        property_id, property_label = await client.search_property(property_query)
        rule = IntentRule(Intent.GENERIC, property_id, property_label, ())
    source_url = f"https://www.wikidata.org/wiki/{person_qid}"
    if rule.intent is Intent.SUMMARY:
        summary = await client.get_wikipedia_summary(entity)
        values = [summary or person.description]
        resolution = "wikipedia_summary" if summary else "wikidata_description"
        wikipedia_title = entity.get("sitelinks", {}).get("frwiki", {}).get("title")
        if summary and wikipedia_title:
            source_url = f"https://fr.wikipedia.org/wiki/{quote(wikipedia_title.replace(' ', '_'))}"
    else:
        values = await format_claims(client, entity, rule.property_id)
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
            resolution=resolution,
        ),
    )
