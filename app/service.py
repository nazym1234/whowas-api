import re
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote

from app.intents import (
    IntentRule,
    asks_for_count,
    extract_property_query,
    normalize,
)
from app.models import (
    Action,
    AnswerResponse,
    Evidence,
    EvidenceDetail,
    Intent,
    Person,
    PersonCandidate,
)
from app.query import QuestionPlan, analyze_question
from app.wikidata import WikidataClient, claim_values, format_claims, format_time, localized_value

PERSON_RELATION_PROPERTIES = {"P22", "P25", "P26", "P40", "P3373"}


class AmbiguousPersonError(ValueError):
    def __init__(self, searched_name: str, candidates: list[PersonCandidate]) -> None:
        super().__init__(f"Plusieurs personnes correspondent à « {searched_name} ».")
        self.searched_name = searched_name
        self.candidates = candidates


def _person_from_entity(qid: str, entity: dict[str, Any]) -> Person:
    images = claim_values(entity, "P18")
    image_url = None
    if images and images[0].get("type") == "string":
        filename = str(images[0].get("value", "")).replace(" ", "_")
        image_url = f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{quote(filename)}"
    return Person(
        qid=qid,
        name=localized_value(entity.get("labels", {})),
        description=localized_value(entity.get("descriptions", {})),
        image_url=image_url,
    )


async def _related_people(
    client: WikidataClient,
    entity: dict[str, Any],
    property_id: str,
) -> list[Person]:
    if property_id not in PERSON_RELATION_PROPERTIES:
        return []
    qids = [
        str(value.get("value", {}).get("id"))
        for value in claim_values(entity, property_id)
        if value.get("type") == "wikibase-entityid"
    ][:10]
    people: list[Person] = []
    for qid in qids:
        related_entity = await client.get_entity(qid)
        people.append(_person_from_entity(qid, related_entity))
    return people


async def resolve_person(
    client: WikidataClient,
    searched_name: str | None,
    selected_qid: str | None = None,
) -> tuple[Person, dict[str, Any], float]:
    if selected_qid:
        entity = await client.get_entity(selected_qid)
        return _person_from_entity(selected_qid, entity), entity, 1.0
    if not searched_name:
        raise ValueError("Indiquez le nom de la personne dans la question.")

    candidates = await client.search_people(searched_name)
    if not candidates:
        qid, entity = await client.search_person(searched_name)
        return _person_from_entity(qid, entity), entity, 0.7
    exact = [item for item in candidates if item.name.casefold() == searched_name.casefold()]
    if len(exact) > 1:
        raise AmbiguousPersonError(searched_name, exact[:5])
    if len(candidates) > 1 and candidates[0].score - candidates[1].score < 0.05:
        raise AmbiguousPersonError(searched_name, candidates[:5])
    selected = candidates[0]
    entity = await client.get_entity(selected.qid)
    return _person_from_entity(selected.qid, entity), entity, selected.score


def _claim_date(entity: dict[str, Any], property_id: str) -> date | None:
    values = claim_values(entity, property_id)
    if not values or values[0].get("type") != "time":
        return None
    raw = str(values[0].get("value", {}).get("time", "")).lstrip("+")
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _years_between(start: date, end: date) -> int:
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def _age_answer(person: Person, entity: dict[str, Any], lifespan: bool = False) -> str:
    birth = _claim_date(entity, "P569")
    death = _claim_date(entity, "P570")
    if birth is None:
        return f"Wikidata ne fournit pas de date de naissance exploitable pour {person.name}."
    if lifespan:
        if death is None:
            current_age = _years_between(birth, date.today())
            return f"{person.name} est en vie d'après Wikidata et a {current_age} ans."
        return f"{person.name} a vécu {_years_between(birth, death)} ans."
    reference = death or date.today()
    age = _years_between(birth, reference)
    if death:
        return f"{person.name} est décédé(e) à l'âge de {age} ans."
    return f"{person.name} a {age} ans."


DEMONYM_COUNTRIES = {
    "algerien": "algérie",
    "algerienne": "algérie",
    "allemand": "allemagne",
    "allemande": "allemagne",
    "americain": "états-unis",
    "americaine": "états-unis",
    "australien": "australie",
    "australienne": "australie",
    "britannique": "royaume-uni",
    "canadien": "canada",
    "canadienne": "canada",
    "espagnol": "espagne",
    "espagnole": "espagne",
    "francais": "france",
    "francaise": "france",
    "italien": "italie",
    "italienne": "italie",
    "polonais": "pologne",
    "polonaise": "pologne",
}


def _verification_answer(person: Person, question: str, values: list[str]) -> str:
    normalized_question = normalize(question)
    if re.search(r"\b(?:mort|morts|morte|mortes|decede|decedee)\b", normalized_question):
        if values:
            return f"Oui, {person.name} est décédé(e) d'après Wikidata : {values[0]}."
        return (
            f"Wikidata ne fournit pas de date de décès pour {person.name}. "
            "Cela ne suffit pas à confirmer que cette personne est en vie."
        )
    expected = [
        country for demonym, country in DEMONYM_COUNTRIES.items() if demonym in normalized_question
    ]
    normalized_values = [normalize(value) for value in values]
    confirmed = any(
        value in normalized_question or any(normalize(target) in value for target in expected)
        for value in normalized_values
    )
    if confirmed:
        return f"Oui, cette affirmation est confirmée pour {person.name} par Wikidata."
    return (
        f"Cette affirmation n'est pas confirmée pour {person.name} par les données "
        "Wikidata disponibles. Cela ne prouve pas nécessairement qu'elle est fausse."
    )


def _qualifier_date(statement: dict[str, Any], property_id: str) -> str | None:
    qualifiers = statement.get("qualifiers", {}).get(property_id, [])
    if not qualifiers:
        return None
    value = qualifiers[0].get("datavalue", {}).get("value", {})
    raw_time = value.get("time")
    return format_time(raw_time) if raw_time else None


def _qualifier_as_date(statement: dict[str, Any], property_id: str) -> date | None:
    qualifiers = statement.get("qualifiers", {}).get(property_id, [])
    if not qualifiers:
        return None
    raw_time = str(qualifiers[0].get("datavalue", {}).get("value", {}).get("time", ""))
    try:
        return date.fromisoformat(raw_time.lstrip("+")[:10])
    except ValueError:
        return None


def _duration_answer(
    person: Person,
    entity: dict[str, Any],
    property_id: str,
    property_label: str,
    values: list[str],
) -> str:
    statements = entity.get("claims", {}).get(property_id, [])
    periods: list[str] = []
    for value, statement in zip(values, statements, strict=False):
        start = _qualifier_as_date(statement, "P580")
        end = _qualifier_as_date(statement, "P582")
        if start:
            years = _years_between(start, end or date.today())
            periods.append(f"{value} : {years} an(s)")
    if not periods:
        return (
            f"Wikidata ne fournit pas assez de dates pour calculer la durée de "
            f"« {property_label} » concernant {person.name}."
        )
    return f"Pour {person.name}, les durées calculées sont : {', '.join(periods)}."


def _evidence_details(
    entity: dict[str, Any],
    property_id: str,
    values: list[str],
) -> list[EvidenceDetail]:
    statements = [
        statement
        for statement in entity.get("claims", {}).get(property_id, [])
        if statement.get("rank") != "deprecated"
    ]
    return [
        EvidenceDetail(
            value=value,
            statement_id=statement.get("id"),
            rank=statement.get("rank", "normal"),
            start_date=_qualifier_date(statement, "P580"),
            end_date=_qualifier_date(statement, "P582"),
        )
        for value, statement in zip(values, statements, strict=False)
    ]


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
        "generic": (
            f"Pour « {rule.property_label} », Wikidata indique pour {person_name} : {joined}."
        ),
    }
    return templates[rule.intent.value]


async def answer_question(
    client: WikidataClient,
    question: str,
    person_qid: str | None = None,
    context_qid: str | None = None,
) -> AnswerResponse:
    plan: QuestionPlan = analyze_question(question, has_context=bool(context_qid))
    rule = plan.rule
    resolution = "rule" if rule else "dynamic_property"
    names = [name for name in plan.person_names if name != "__context__"]
    selected_qid = person_qid or (context_qid if not names else None)
    searched_name = names[0] if names else None
    person, entity, person_confidence = await resolve_person(
        client,
        searched_name,
        selected_qid,
    )

    if plan.action is Action.AGE or (plan.action is Action.DURATION and rule is None):
        lifespan = plan.action is Action.DURATION
        answer = _age_answer(person, entity, lifespan)
        values = [answer]
        intent = Intent.LIFESPAN if lifespan else Intent.AGE
        return AnswerResponse(
            person=person,
            question=question,
            intent=intent,
            answer=answer,
            action=plan.action,
            evidence=Evidence(
                property_id="P569+P570" if lifespan else "P569",
                property_label="durée de vie" if lifespan else "âge calculé",
                values=values,
                source_url=f"https://www.wikidata.org/wiki/{person.qid}",
                resolution="calculation",
                confidence=min(plan.confidence, person_confidence),
                retrieved_at=datetime.now(UTC).isoformat(),
            ),
        )

    if plan.action is Action.DURATION and rule is not None:
        values = await format_claims(client, entity, rule.property_id)
        answer = _duration_answer(
            person,
            entity,
            rule.property_id,
            rule.property_label,
            values,
        )
        return AnswerResponse(
            person=person,
            question=question,
            intent=rule.intent,
            answer=answer,
            action=Action.DURATION,
            evidence=Evidence(
                property_id=rule.property_id,
                property_label=rule.property_label,
                values=values,
                source_url=f"https://www.wikidata.org/wiki/{person.qid}",
                resolution="qualifier_duration",
                confidence=min(plan.confidence, person_confidence),
                retrieved_at=datetime.now(UTC).isoformat(),
                details=_evidence_details(entity, rule.property_id, values),
            ),
        )

    if plan.action is Action.COMPARE and len(names) >= 2:
        other, other_entity, other_confidence = await resolve_person(client, names[1])
        property_id = rule.property_id if rule else "P569"
        property_label = rule.property_label if rule else "date de naissance"
        if property_id == "P569":
            first_birth = _claim_date(entity, "P569")
            second_birth = _claim_date(other_entity, "P569")
            if first_birth and second_birth:
                older = person if first_birth < second_birth else other
                answer = (
                    f"{older.name} est la personne la plus âgée : {person.name} est né(e) le "
                    f"{first_birth.isoformat()} et {other.name} le {second_birth.isoformat()}."
                )
                values = [first_birth.isoformat(), second_birth.isoformat()]
            else:
                answer = (
                    "La comparaison est impossible car une date de naissance manque dans Wikidata."
                )
                values = []
        else:
            first_values = await format_claims(client, entity, property_id)
            second_values = await format_claims(client, other_entity, property_id)
            normalized_question = normalize(question)
            if "meme" in normalized_question:
                common = sorted(set(first_values) & set(second_values))
                answer = (
                    f"{person.name} et {other.name} ont {len(common)} valeur(s) commune(s) "
                    f"pour « {property_label} » : {', '.join(common) or 'aucune'} ."
                )
            else:
                winner = person if len(first_values) >= len(second_values) else other
                answer = (
                    f"{winner.name} possède le plus de valeurs documentées pour "
                    f"« {property_label} » : {len(first_values)} pour {person.name}, "
                    f"{len(second_values)} pour {other.name}."
                )
            values = first_values + second_values
        return AnswerResponse(
            person=person,
            related_people=[other],
            question=question,
            intent=Intent.COMPARISON,
            answer=answer,
            action=Action.COMPARE,
            evidence=Evidence(
                property_id=property_id,
                property_label=f"comparaison : {property_label}",
                values=values,
                source_url=f"https://www.wikidata.org/wiki/{person.qid}",
                resolution="comparison",
                confidence=min(plan.confidence, person_confidence, other_confidence),
                retrieved_at=datetime.now(UTC).isoformat(),
            ),
        )

    if rule is None:
        property_query = extract_property_query(question, searched_name or person.name)
        properties = await client.search_properties(property_query)
        if not properties:
            raise ValueError(f"La propriété « {property_query} » n'a pas été trouvée.")
        property_id, property_label = next(
            (
                (candidate_id, candidate_label)
                for candidate_id, candidate_label in properties
                if candidate_id in entity.get("claims", {})
            ),
            properties[0],
        )
        rule = IntentRule(Intent.GENERIC, property_id, property_label, ())
    source_url = f"https://www.wikidata.org/wiki/{person.qid}"
    if rule.intent is Intent.SUMMARY:
        summary = await client.get_wikipedia_summary(entity)
        values = [summary or person.description]
        resolution = "wikipedia_summary" if summary else "wikidata_description"
        wikipedia_title = entity.get("sitelinks", {}).get("frwiki", {}).get("title")
        if summary and wikipedia_title:
            source_url = f"https://fr.wikipedia.org/wiki/{quote(wikipedia_title.replace(' ', '_'))}"
    else:
        current_only = any(
            token in normalize(question) for token in ("actuel", "actuelle", "actuellement")
        )
        values = await format_claims(
            client,
            entity,
            rule.property_id,
            current_only=current_only,
        )
    answer = build_answer(person.name, rule, values, asks_for_count(question))
    if plan.action is Action.VERIFY:
        answer = _verification_answer(person, question, values)
    related_people = await _related_people(client, entity, rule.property_id)
    return AnswerResponse(
        person=person,
        related_people=related_people,
        question=question,
        intent=rule.intent,
        answer=answer,
        action=plan.action,
        evidence=Evidence(
            property_id=rule.property_id,
            property_label=rule.property_label,
            values=values,
            source_url=source_url,
            resolution=resolution,
            confidence=min(plan.confidence, person_confidence),
            retrieved_at=datetime.now(UTC).isoformat(),
            details=_evidence_details(entity, rule.property_id, values),
        ),
    )


async def answer_group_question(
    client: WikidataClient,
    question: str,
    qids: list[str],
) -> AnswerResponse:
    responses = [await answer_question(client, question, person_qid=qid) for qid in qids[:10]]
    first = responses[0]
    people = [response.person for response in responses]
    answers = [f"{response.person.name} : {response.answer}" for response in responses]
    values = [value for response in responses for value in response.evidence.values]
    return AnswerResponse(
        person=first.person,
        related_people=people[1:],
        question=question,
        intent=first.intent,
        answer=" ".join(answers),
        action=first.action,
        evidence=Evidence(
            property_id=first.evidence.property_id,
            property_label=first.evidence.property_label,
            values=values,
            source_url=first.evidence.source_url,
            resolution="conversation_group",
            confidence=min(response.evidence.confidence for response in responses),
            retrieved_at=datetime.now(UTC).isoformat(),
        ),
    )
