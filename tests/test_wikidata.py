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
