from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

import httpx

from app.cache import TTLCache
from app.models import PersonCandidate
from app.observability import metrics

API_URL = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API_URL = "https://fr.wikipedia.org/w/api.php"
USER_AGENT = "WhoWas/4.0 (https://github.com/nazym1234/whowas-api)"


class UpstreamUnavailableError(RuntimeError):
    pass


class WikidataClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(10, connect=5),
            transport=transport,
            trust_env=False,
        )
        self.cache = TTLCache(max_size=512)
        self._semaphore = asyncio.Semaphore(8)
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    async def _request_json(
        self,
        url: str,
        params: dict[str, str],
        *,
        ttl: float = 900,
    ) -> dict[str, Any]:
        cache_key = f"{url}?{json.dumps(params, sort_keys=True, ensure_ascii=False)}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            metrics.increment("cache_hits_total")
            return cached
        metrics.increment("cache_misses_total")
        if time.monotonic() < self._circuit_open_until:
            raise UpstreamUnavailableError("Le service externe est temporairement protégé.")

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with self._semaphore:
                    metrics.increment(
                        "wikipedia_requests_total"
                        if "wikipedia.org" in url
                        else "wikidata_requests_total"
                    )
                    response = await self.client.get(url, params=params)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                data = response.json()
                self._consecutive_failures = 0
                await self.cache.set(cache_key, data, ttl)
                return data
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                metrics.increment("upstream_errors_total")
                self._consecutive_failures += 1
                if attempt < 2:
                    await asyncio.sleep(0.1 * (2**attempt))

        if self._consecutive_failures >= 5:
            self._circuit_open_until = time.monotonic() + 30
        raise UpstreamUnavailableError("Wikidata ou Wikipédia ne répond pas.") from last_error

    async def close(self) -> None:
        await self.client.aclose()

    @property
    def is_available(self) -> bool:
        return time.monotonic() >= self._circuit_open_until

    async def get_entity(self, qid: str) -> dict[str, Any]:
        data = await self._request_json(
            API_URL,
            {
                "action": "wbgetentities",
                "ids": qid,
                "props": "labels|descriptions|claims|sitelinks",
                "languages": "fr|en",
                "languagefallback": "1",
                "format": "json",
                "origin": "*",
            },
        )
        entities = data.get("entities", {})
        entity = entities.get(qid)
        if not entity or entity.get("missing") is not None:
            raise LookupError(f"La personne {qid} n'existe pas dans Wikidata.")
        return entity

    async def search_person(self, name: str) -> tuple[str, dict[str, Any]]:
        data = await self._request_json(
            API_URL,
            {
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
        candidate_ids = [result.get("id") for result in data.get("search", [])]
        if not candidate_ids:
            fallback = await self._request_json(
                API_URL,
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": name,
                    "srnamespace": "0",
                    "srlimit": "5",
                    "format": "json",
                    "origin": "*",
                },
            )
            candidate_ids = [
                result.get("title") for result in fallback.get("query", {}).get("search", [])
            ]
        for qid in candidate_ids:
            if not qid:
                continue
            entity = await self.get_entity(qid)
            instance_ids = {
                value["value"]["id"]
                for value in claim_values(entity, "P31")
                if value.get("type") == "wikibase-entityid" and "id" in value.get("value", {})
            }
            if "Q5" in instance_ids:
                return qid, entity
        raise LookupError(f"Aucune personnalité trouvée pour « {name} » dans Wikidata.")

    async def search_people(self, name: str) -> list[PersonCandidate]:
        data = await self._request_json(
            API_URL,
            {
                "action": "wbsearchentities",
                "search": name,
                "language": "fr",
                "uselang": "fr",
                "type": "item",
                "limit": "8",
                "format": "json",
                "origin": "*",
            },
            ttl=1800,
        )
        candidates: list[PersonCandidate] = []
        normalized_name = name.casefold()
        for result in data.get("search", []):
            qid = result.get("id")
            if not qid:
                continue
            entity = await self.get_entity(qid)
            instance_ids = {
                value["value"]["id"]
                for value in claim_values(entity, "P31")
                if value.get("type") == "wikibase-entityid" and "id" in value.get("value", {})
            }
            if "Q5" not in instance_ids:
                continue
            label = localized_value(entity.get("labels", {}))
            score = SequenceMatcher(None, normalized_name, label.casefold()).ratio()
            candidates.append(
                PersonCandidate(
                    qid=qid,
                    name=label,
                    description=localized_value(entity.get("descriptions", {})),
                    score=round(score, 3),
                )
            )
        return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)

    async def get_labels(self, qids: set[str], language: str = "fr") -> dict[str, str]:
        if not qids:
            return {}
        data = await self._request_json(
            API_URL,
            {
                "action": "wbgetentities",
                "ids": "|".join(sorted(qids)),
                "props": "labels",
                "languages": f"{language}|en",
                "format": "json",
                "origin": "*",
            },
            ttl=3600,
        )
        labels: dict[str, str] = {}
        for qid, entity in data.get("entities", {}).items():
            available = entity.get("labels", {})
            label = available.get(language) or available.get("en")
            labels[qid] = label["value"] if label else qid
        return labels

    async def search_property(self, query: str) -> tuple[str, str]:
        results = await self.search_properties(query)
        if not results:
            raise ValueError(f"La propriété « {query} » n'a pas été trouvée dans Wikidata.")
        return results[0]

    async def search_properties(self, query: str) -> list[tuple[str, str]]:
        data = await self._request_json(
            API_URL,
            {
                "action": "wbsearchentities",
                "search": query,
                "language": "fr",
                "uselang": "fr",
                "type": "property",
                "limit": "5",
                "format": "json",
                "origin": "*",
            },
            ttl=3600,
        )
        results = data.get("search", [])
        return [
            (result["id"], result.get("label") or query)
            for result in results
            if result.get("id", "").startswith("P")
        ]

    async def get_wikipedia_summary(self, entity: dict[str, Any]) -> str | None:
        title = entity.get("sitelinks", {}).get("frwiki", {}).get("title")
        if not title:
            return None
        data = await self._request_json(
            WIKIPEDIA_API_URL,
            {
                "action": "query",
                "prop": "extracts",
                "exintro": "1",
                "explaintext": "1",
                "redirects": "1",
                "titles": title,
                "format": "json",
                "origin": "*",
            },
            ttl=3600,
        )
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None
        extract = next(iter(pages.values())).get("extract", "").strip()
        return extract or None


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
    *,
    current_only: bool = False,
) -> list[str]:
    statements = entity.get("claims", {}).get(property_id, [])
    if current_only:
        statements = [
            statement for statement in statements if "P582" not in statement.get("qualifiers", {})
        ]
    statements = sorted(
        statements,
        key=lambda statement: statement.get("rank") == "preferred",
        reverse=True,
    )
    raw_values = [
        datavalue
        for statement in statements
        if statement.get("rank") != "deprecated"
        if (datavalue := statement.get("mainsnak", {}).get("datavalue"))
    ]
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
        elif value.get("type") == "quantity":
            amount = str(value["value"].get("amount", "")).lstrip("+")
            unit_url = value["value"].get("unit", "")
            unit_id = unit_url.rsplit("/", 1)[-1] if unit_url else ""
            units = {
                "Q11573": "m",
                "Q174728": "cm",
                "Q712226": "km",
                "Q41803": "g",
                "Q11570": "kg",
                "Q7727": "min",
                "Q25235": "h",
            }
            formatted.append(f"{amount} {units.get(unit_id, '')}".strip())
        elif value.get("type") == "monolingualtext":
            formatted.append(str(value["value"].get("text", "")))
        elif value.get("type") == "globecoordinate":
            latitude = value["value"].get("latitude")
            longitude = value["value"].get("longitude")
            formatted.append(f"{latitude}, {longitude}")
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
