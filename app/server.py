"""Local HTTP boundary between the browser interface and Python game state."""

import json
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.backend.state import GameState
from app.core.hero_mastery import POSITIONS

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
STATIC_DIRECTORY = PROJECT_DIRECTORY / "app" / "frontend" / "static"
RELATIONSHIP_TYPES = ["synergy", "counter", "countered_by", "anti_synergy"]

# -----------------------------------------------------------------------------
# Server Config
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app):
    # Authoritative state object for the app.
    app.state.game = GameState()
    yield

# Setup server
app = FastAPI(
    title="Lazy Esports Godfather",
    lifespan=lifespan,
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


# Pydantic models for updates
class MasteryUpdate(BaseModel):
    position: str
    levels: dict[str, int]

class DraftOrderUpdate(BaseModel):
    steps: list[tuple[str, str]]

class StartDraftRequest(BaseModel):
    player_side: str

class DraftActionRequest(BaseModel):
    hero: str
    position: str | None = None

class CoachRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)

class ModelSettingsUpdate(BaseModel):
    provider: str
    model: str
    base_url: str = ""
    api_key: str = ""


# -----------------------------------------------------------------------------
# Frontend and initial application data
# -----------------------------------------------------------------------------

# Index
@app.get("/")
def index():
    return FileResponse(STATIC_DIRECTORY / "index.html")

# Bootstrap
@app.get("/api/bootstrap")
def bootstrap():
    game = app.state.game
    with game.lock:
        return game.bootstrap_payload()


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------


@app.put("/api/settings/model")
def update_model_settings(update: ModelSettingsUpdate):
    game = app.state.game
    try:
        with game.lock:
            return game.configure_model(
                update.provider,
                update.model,
                update.base_url,
                update.api_key,
            )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


# -----------------------------------------------------------------------------
# Team masteries
# -----------------------------------------------------------------------------

@app.put("/api/masteries/{team}")
def update_masteries(team: str, update: MasteryUpdate):
    if team not in {"t1", "t2"}:
        raise HTTPException(404, "Unknown team.")
    if update.position not in POSITIONS:
        raise HTTPException(400, "Unknown position.")

    game = app.state.game
    try:
        with game.lock:
            return game.set_masteries(team, update.position, update.levels)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


# -----------------------------------------------------------------------------
# Master graph
# -----------------------------------------------------------------------------

@app.get("/api/graph/{hero}")
def graph_relationships(
    hero: str,
    relationship_type: Annotated[list[str] | None, Query()] = None,
):
    relationship_type = relationship_type or RELATIONSHIP_TYPES
    invalid_types = set(relationship_type) - set(RELATIONSHIP_TYPES)
    if invalid_types:
        raise HTTPException(400, f"Unknown relationship types: {sorted(invalid_types)}")

    game = app.state.game
    try:
        with game.lock:
            return {
                "hero": hero,
                "relationships": game.graph_relationships(hero, relationship_type),
            }
    except ValueError as error:
        raise HTTPException(404, str(error)) from error


# -----------------------------------------------------------------------------
# Draft order and draft actions
# -----------------------------------------------------------------------------

@app.put("/api/draft-order")
def update_draft_order(update: DraftOrderUpdate):
    if not update.steps:
        raise HTTPException(400, "The draft order cannot be empty.")
    for side, action in update.steps:
        if side not in {"blue", "red"} or action not in {"Pick", "Ban"}:
            raise HTTPException(400, "Each step needs a valid side and action.")

    game = app.state.game
    with game.lock:
        draft_order = game.set_draft_order(update.steps)
        return {"draft_order": draft_order}


@app.post("/api/draft/start")
def start_draft(request: StartDraftRequest):
    if request.player_side not in {"blue", "red"}:
        raise HTTPException(400, "Player side must be blue or red.")

    game = app.state.game
    with game.lock:
        game.start_draft(request.player_side)
        return game.draft_payload()


@app.post("/api/draft/action")
def apply_draft_action(request: DraftActionRequest):
    game = app.state.game
    try:
        with game.lock:
            game.apply_draft_action(request.hero, request.position)
            return game.draft_payload()
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.post("/api/draft/apply-t2")
def apply_t2_knowledge():
    game = app.state.game
    try:
        with game.lock:
            game.apply_t2_knowledge()
            return game.draft_payload()
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.delete("/api/draft")
def end_draft():
    game = app.state.game
    with game.lock:
        game.end_draft()
        return {"ok": True}


# -----------------------------------------------------------------------------
# Coach
# -----------------------------------------------------------------------------

@app.post("/api/coach")
def send_coach_message(request: CoachRequest):
    game = app.state.game
    if not game.ai_enabled:
        raise HTTPException(
            503,
            "No AI model is configured. The graph and draft tools remain available.",
        )

    def stream_response():
        try:
            with game.lock:
                for text in game.stream_coach_message(request.message):
                    yield json.dumps({"text": text}) + "\n"
        except Exception as error:
            yield json.dumps({"error": f"The coach could not respond: {error}"}) + "\n"

    return StreamingResponse(
        stream_response(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )


@app.delete("/api/coach")
def clear_coach():
    game = app.state.game
    with game.lock:
        game.clear_coach_messages()
        return {"ok": True}


def main():
    host = "127.0.0.1"
    port = 8765
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(app, host=host, port=port)
