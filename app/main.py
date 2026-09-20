import json
import logging
import re
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.akinator import AkinatorEngine
from app.intents import RULES, normalize
from app.models import AkinatorAnswerRequest, AnswerResponse, QuestionRequest
from app.observability import metrics
from app.rate_limit import SlidingWindowRateLimiter
from app.service import AmbiguousPersonError, answer_group_question, answer_question
from app.wikidata import UpstreamUnavailableError, WikidataClient

rate_limiter = SlidingWindowRateLimiter(limit=30, window_seconds=60)
akinator = AkinatorEngine()
logger = logging.getLogger("whowas")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def resolve_contextual_question(payload: QuestionRequest) -> str:
    normalized_question = normalize(payload.question)
    previous_question = normalize(payload.context_question or "")
    asks_elliptical_year = bool(
        re.match(
            r"^\s*(?:et\s+)?(?:en\s+)?quelle\s+annee\b",
            normalized_question,
        )
    )
    if not asks_elliptical_year or not payload.context_qid:
        return payload.question
    if "mort" in previous_question or "decede" in previous_question:
        return "Quand est-elle décédée ?"
    if re.search(r"\bnee?\b", previous_question) or payload.context_property_id == "P569":
        return "Quand est-elle née ?"
    return payload.question


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.wikidata = WikidataClient()
    yield
    await app.state.wikidata.close()


app = FastAPI(
    title="WhoWas API",
    description="Moteur explicable de questions biographiques fondé sur Wikidata et Wikipédia.",
    version="4.4.1",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def security_and_observability(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    duration = time.perf_counter() - started
    metrics.observe_request(duration)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' https://commons.wikimedia.org "
        "https://upload.wikimedia.org data:; "
        "style-src 'self'; script-src 'self'; connect-src 'self'"
    )
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
        )
    )
    return response


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness(request: Request) -> dict[str, object]:
    client = request.app.state.wikidata
    return {
        "status": "ready" if client.is_available else "degraded",
        "cache_entries": client.cache.size,
        "circuit_open": not client.is_available,
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    return metrics.render()


@app.get("/people/search")
async def search_people(q: str, request: Request):
    if len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail="Saisissez au moins deux caractères.")
    return await request.app.state.wikidata.search_people(q.strip())


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


@app.post("/akinator/start")
async def start_akinator() -> dict[str, object]:
    return akinator.start()


@app.post("/akinator/answer")
async def answer_akinator(payload: AkinatorAnswerRequest) -> dict[str, object]:
    try:
        return akinator.answer(payload.session_id, payload.answer)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/answer", response_model=AnswerResponse)
async def answer(payload: QuestionRequest, request: Request) -> AnswerResponse:
    client_key = request.client.host if request.client else "unknown"
    if not await rate_limiter.allow(client_key):
        metrics.increment("rate_limited_total")
        raise HTTPException(status_code=429, detail="Trop de requêtes. Réessayez dans une minute.")
    try:
        effective_question = resolve_contextual_question(payload)
        normalized_question = normalize(payload.question)
        plural_reference = re.search(
            r"\b(?:ils|elles|eux|leur|leurs)\b",
            normalized_question,
        )
        if plural_reference and len(payload.context_qids) > 1 and not payload.person_qid:
            return await answer_group_question(
                request.app.state.wikidata,
                effective_question,
                payload.context_qids,
            )
        ordinal_qid = None
        if payload.context_qids and re.search(r"\b(?:le )?premier\b", normalized_question):
            ordinal_qid = payload.context_qids[0]
        elif len(payload.context_qids) > 1 and re.search(
            r"\b(?:le )?(?:deuxieme|second)\b", normalized_question
        ):
            ordinal_qid = payload.context_qids[1]
        return await answer_question(
            request.app.state.wikidata,
            effective_question,
            payload.person_qid or ordinal_qid,
            payload.context_qid,
        )
    except AmbiguousPersonError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "searched_name": exc.searched_name,
                "candidates": [candidate.model_dump() for candidate in exc.candidates],
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Wikidata est temporairement indisponible. Réessayez dans un instant.",
        ) from exc
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Wikidata ou Wikipédia est temporairement indisponible.",
        ) from exc
