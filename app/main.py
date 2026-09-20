from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.intents import RULES
from app.models import AnswerResponse, QuestionRequest
from app.service import answer_question
from app.wikidata import WikidataClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.wikidata = WikidataClient()
    yield
    await app.state.wikidata.close()


app = FastAPI(
    title="WhoWas API",
    description="Questions biographiques simples fondées sur Wikidata.",
    version="2.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/intents")
async def list_intents() -> list[dict[str, object]]:
    return [
        {
            "name": rule.intent,
            "wikidata_property": rule.property_id,
            "label": rule.property_label,
        }
        for rule in RULES
    ]


@app.post("/answer", response_model=AnswerResponse)
async def answer(payload: QuestionRequest, request: Request) -> AnswerResponse:
    try:
        return await answer_question(
            request.app.state.wikidata,
            payload.question,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Wikidata est temporairement indisponible. Réessayez dans un instant.",
        ) from exc
