import asyncio

import httpx

from app.wikidata import API_URL, WikidataClient, format_claims


def test_get_entity_uses_wikidata_api() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(API_URL)
        assert request.url.params["action"] == "wbgetentities"
        assert request.url.params["ids"] == "Q7186"
        return httpx.Response(
            200,
            json={
                "entities": {
                    "Q7186": {
                        "id": "Q7186",
                        "labels": {"fr": {"value": "Marie Curie"}},
                        "claims": {},
                    }
                }
            },
        )

    async def run() -> None:
        client = WikidataClient(transport=httpx.MockTransport(handler))
        try:
            entity = await client.get_entity("Q7186")
            assert entity["labels"]["fr"]["value"] == "Marie Curie"
        finally:
            await client.close()

    asyncio.run(run())


def test_get_entity_rejects_missing_entity() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entities": {"Q0": {"missing": ""}}})

    async def run() -> None:
        client = WikidataClient(transport=httpx.MockTransport(handler))
        try:
            try:
                await client.get_entity("Q0")
            except LookupError as exc:
                assert "n'existe pas" in str(exc)
            else:
                raise AssertionError("Une entité absente doit produire LookupError")
        finally:
            await client.close()

    asyncio.run(run())


def test_search_person_keeps_a_human_result() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        action = request.url.params["action"]
        if action == "wbsearchentities":
            assert request.url.params["search"] == "Marie Curie"
            return httpx.Response(200, json={"search": [{"id": "Q7186"}]})
        assert action == "wbgetentities"
        return httpx.Response(
            200,
            json={
                "entities": {
                    "Q7186": {
                        "id": "Q7186",
                        "labels": {"fr": {"value": "Marie Curie"}},
                        "descriptions": {"fr": {"value": "physicienne et chimiste"}},
                        "claims": {
                            "P31": [
                                {
                                    "mainsnak": {
                                        "datavalue": {
                                            "type": "wikibase-entityid",
                                            "value": {"id": "Q5"},
                                        }
                                    }
                                }
                            ]
                        },
                    }
                }
            },
        )

    async def run() -> None:
        client = WikidataClient(transport=httpx.MockTransport(handler))
        try:
            qid, entity = await client.search_person("Marie Curie")
            assert qid == "Q7186"
            assert entity["labels"]["fr"]["value"] == "Marie Curie"
        finally:
            await client.close()

    asyncio.run(run())


def test_request_retries_then_uses_cache() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        client = WikidataClient(transport=httpx.MockTransport(handler))
        try:
            first = await client._request_json(API_URL, {"test": "retry"})
            second = await client._request_json(API_URL, {"test": "retry"})
            assert first == second == {"ok": True}
            assert calls == 2
        finally:
            await client.close()

    asyncio.run(run())


def test_search_people_filters_non_humans() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["action"] == "wbsearchentities":
            return httpx.Response(
                200,
                json={"search": [{"id": "Q1"}, {"id": "Q2"}]},
            )
        qid = request.url.params["ids"]
        instance = "Q5" if qid == "Q1" else "Q43229"
        return httpx.Response(
            200,
            json={
                "entities": {
                    qid: {
                        "labels": {
                            "fr": {"value": "Ada Lovelace" if qid == "Q1" else "Organisation"}
                        },
                        "descriptions": {"fr": {"value": "Description"}},
                        "claims": {
                            "P31": [
                                {
                                    "mainsnak": {
                                        "datavalue": {
                                            "type": "wikibase-entityid",
                                            "value": {"id": instance},
                                        }
                                    }
                                }
                            ]
                        },
                    }
                }
            },
        )

    async def run() -> None:
        client = WikidataClient(transport=httpx.MockTransport(handler))
        try:
            candidates = await client.search_people("Ada Lovelace")
            assert [candidate.qid for candidate in candidates] == ["Q1"]
            assert candidates[0].score == 1.0
        finally:
            await client.close()

    asyncio.run(run())


def test_property_search_and_wikipedia_summary() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "fr.wikipedia.org":
            return httpx.Response(
                200,
                json={"query": {"pages": {"1": {"extract": "Un résumé."}}}},
            )
        return httpx.Response(
            200,
            json={
                "search": [
                    {"id": "P1340", "label": "couleur des yeux"},
                    {"id": "Q1", "label": "ignoré"},
                ]
            },
        )

    async def run() -> None:
        client = WikidataClient(transport=httpx.MockTransport(handler))
        try:
            properties = await client.search_properties("couleur yeux")
            assert properties == [("P1340", "couleur des yeux")]
            summary = await client.get_wikipedia_summary(
                {"sitelinks": {"frwiki": {"title": "Exemple"}}}
            )
            assert summary == "Un résumé."
            assert await client.get_wikipedia_summary({}) is None
        finally:
            await client.close()

    asyncio.run(run())


def test_format_additional_datatypes_and_current_values() -> None:
    entity = {
        "claims": {
            "P1": [
                {
                    "mainsnak": {
                        "datavalue": {
                            "type": "quantity",
                            "value": {
                                "amount": "+1.80",
                                "unit": "http://www.wikidata.org/entity/Q11573",
                            },
                        }
                    }
                },
                {
                    "mainsnak": {
                        "datavalue": {
                            "type": "monolingualtext",
                            "value": {"text": "bonjour", "language": "fr"},
                        }
                    }
                },
                {
                    "mainsnak": {
                        "datavalue": {
                            "type": "globecoordinate",
                            "value": {"latitude": 1.2, "longitude": 3.4},
                        }
                    }
                },
            ],
            "P26": [
                {"mainsnak": {"datavalue": {"type": "string", "value": "actuel"}}},
                {
                    "mainsnak": {"datavalue": {"type": "string", "value": "ancien"}},
                    "qualifiers": {"P582": [{}]},
                },
            ],
        }
    }

    async def run() -> None:
        client = WikidataClient(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
        try:
            assert await format_claims(client, entity, "P1") == ["1.80 m", "bonjour", "1.2, 3.4"]
            assert await format_claims(client, entity, "P26", current_only=True) == ["actuel"]
        finally:
            await client.close()

    asyncio.run(run())
