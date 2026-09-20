from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "WhoWas/1.0 (https://github.com/nazym1234/whowas-api)"


class WikidataClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=10,
            transport=transport,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def get_entity(self, qid: str) -> dict[str, Any]:
        response = await self.client.get(
            API_URL,
            params={
                "action": "wbgetentities",
                "ids": qid,
                "props": "labels|descriptions|claims",
                "languages": "fr|en",
                "languagefallback": "1",
                "format": "json",
                "origin": "*",
            },
        )
        response.raise_for_status()
        entities = response.json().get("entities", {})
        entity = entities.get(qid)
        if not entity or entity.get("missing") is not None:
            raise LookupError(f"La personne {qid} n'existe pas dans Wikidata.")
        return entity

    async def search_person(self, name: str) -> tuple[str, dict[str, Any]]:
        response = await self.client.get(
            API_URL,
            params={
                "action": "wbsearchentities",
                "search": name,
                "language": "fr",
                "uselang": "fr",
                "type": "item",
                "limit": "5",
                "format": "json",
                "origin": "*",
            },
        )
        response.raise_for_status()
        results = response.json().get("search", [])
        for result in results:
            qid = result.get("id")
            if not qid:
                continue
            entity = await self.get_entity(qid)
            instance_ids = {
                value["value"]["id"]
                for value in claim_values(entity, "P31")
                if value.get("type") == "wikibase-entityid"
                and "id" in value.get("value", {})
            }
            if "Q5" in instance_ids:
                return qid, entity
        raise LookupError(f"Aucune personnalité trouvée pour « {name} » dans Wikidata.")

    async def get_labels(self, qids: set[str], language: str = "fr") -> dict[str, str]:
        if not qids:
            return {}
        response = await self.client.get(
            API_URL,
            params={
                "action": "wbgetentities",
                "ids": "|".join(sorted(qids)),
                "props": "labels",
                "languages": f"{language}|en",
                "format": "json",
                "origin": "*",
            },
        )
        response.raise_for_status()
        labels: dict[str, str] = {}
        for qid, entity in response.json().get("entities", {}).items():
            available = entity.get("labels", {})
            label = available.get(language) or available.get("en")
            labels[qid] = label["value"] if label else qid
        return labels


def localized_value(values: dict[str, Any], language: str = "fr") -> str:
    selected = values.get(language) or values.get("en")
    return selected["value"] if selected else "Information indisponible"


def claim_values(entity: dict[str, Any], property_id: str) -> list[dict[str, Any]]:
    claims = entity.get("claims", {}).get(property_id, [])
    values: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("rank") == "deprecated":
            continue
        datavalue = claim.get("mainsnak", {}).get("datavalue")
        if datavalue:
            values.append(datavalue)
    return values


async def format_claims(
    client: WikidataClient,
    entity: dict[str, Any],
    property_id: str,
) -> list[str]:
    raw_values = claim_values(entity, property_id)
    entity_ids = {
        value["value"]["id"]
        for value in raw_values
        if value.get("type") == "wikibase-entityid" and "id" in value.get("value", {})
    }
    labels = await client.get_labels(entity_ids)
    formatted: list[str] = []
    for value in raw_values:
        if value.get("type") == "wikibase-entityid":
            qid = value["value"]["id"]
            formatted.append(labels.get(qid, qid))
        elif value.get("type") == "time":
            formatted.append(format_time(value["value"].get("time", "")))
        elif value.get("type") in {"string", "external-id"}:
            formatted.append(str(value.get("value")))
    return list(dict.fromkeys(formatted))


def format_time(raw_time: str) -> str:
    cleaned = raw_time.lstrip("+")
    try:
        date = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        months = (
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        )
        return f"{date.day} {months[date.month - 1]} {date.year}"
    except ValueError:
        return raw_time
