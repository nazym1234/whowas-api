import asyncio

import httpx

from app.wikidata import API_URL, WikidataClient


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
