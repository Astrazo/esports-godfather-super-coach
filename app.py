import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core.hero_mastery import POSITIONS
from core.persistence import save_coach_messages, save_draft_order
from web.state import AppState

APP_DIRECTORY = Path(__file__).resolve().parent
STATIC_DIRECTORY = APP_DIRECTORY / "web" / "static"
RELATIONSHIP_TYPES = ["synergy", "counter", "countered_by", "anti_synergy"]


@asynccontextmanager
async def lifespan(app):
    app.state.game = AppState()
    yield


app = FastAPI(
    title="Lazy Esports Godfather",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


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


@app.get("/")
def index():
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/api/bootstrap")
def bootstrap():
    game = app.state.game
    with game.lock:
        return {
            "positions": POSITIONS,
            "heroes": sorted(game.data.hero_names),
            "t1_masteries": game.t1_masteries,
            "t2_masteries": game.t2_masteries,
            "confirmed_t2_positions": sorted(game.confirmed_t2_positions),
            "draft_order": game.draft_order,
            "draft": game.draft_payload(),
            "coach_messages": _visible_messages(game.coach_messages),
            "ai": game.model_settings(),
        }


@app.get("/api/settings/model")
def get_model_settings():
    game = app.state.game
    with game.lock:
        return game.model_settings()


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


@app.put("/api/masteries/{team}")
def update_masteries(team: str, update: MasteryUpdate):
    if team not in {"t1", "t2"}:
        raise HTTPException(404, "Unknown team.")
    if update.position not in POSITIONS:
        raise HTTPException(400, "Unknown position.")

    game = app.state.game
    try:
        with game.lock:
            game.set_masteries(team, update.position, update.levels)
            return {
                "masteries": game.t1_masteries if team == "t1" else game.t2_masteries,
                "confirmed_t2_positions": sorted(game.confirmed_t2_positions),
            }
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


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


@app.put("/api/draft-order")
def update_draft_order(update: DraftOrderUpdate):
    if not update.steps:
        raise HTTPException(400, "The draft order cannot be empty.")
    for side, action in update.steps:
        if side not in {"blue", "red"} or action not in {"Pick", "Ban"}:
            raise HTTPException(400, "Each step needs a valid side and action.")

    game = app.state.game
    with game.lock:
        game.draft_order = update.steps
        save_draft_order(game.draft_order)
        return {"draft_order": game.draft_order}


@app.post("/api/draft/start")
def start_draft(request: StartDraftRequest):
    if request.player_side not in {"blue", "red"}:
        raise HTTPException(400, "Player side must be blue or red.")

    game = app.state.game
    with game.lock:
        game.start_draft(request.player_side)
        return game.draft_payload()


@app.get("/api/draft")
def get_draft():
    game = app.state.game
    with game.lock:
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


@app.post("/api/coach")
def send_coach_message(request: CoachRequest):
    game = app.state.game
    if not game.ai_enabled:
        raise HTTPException(
            503,
            "No AI model is configured. The graph and draft tools remain available.",
        )

    with game.lock:
        game.coach_messages.append({"role": "user", "content": request.message.strip()})
        save_coach_messages(game.coach_messages)

        try:
            result = game.get_agent().invoke({"messages": game.coach_messages})
            game.coach_messages = _serialise_agent_messages(result["messages"])
            save_coach_messages(game.coach_messages)
        except Exception as error:
            raise HTTPException(502, f"The coach could not respond: {error}") from error

        visible_messages = _visible_messages(game.coach_messages)
        return {"message": visible_messages[-1], "messages": visible_messages}


@app.delete("/api/coach")
def clear_coach():
    game = app.state.game
    with game.lock:
        game.coach_messages = []
        save_coach_messages([])
        return {"ok": True}


def _serialise_agent_messages(messages):
    outputs = []
    for message in messages:
        if message.type == "human":
            outputs.append({"role": "human", "content": str(message.text)})
        elif message.type == "ai":
            output = {"role": "ai", "content": str(message.text)}
            if message.tool_calls:
                output["tool_calls"] = [
                    {
                        "id": tool_call["id"],
                        "name": tool_call["name"],
                        "args": tool_call["args"],
                        "type": "tool_call",
                    }
                    for tool_call in message.tool_calls
                ]
            outputs.append(output)
        elif message.type == "tool":
            outputs.append(
                {
                    "role": "tool",
                    "content": str(message.text),
                    "tool_call_id": message.tool_call_id,
                    "name": message.name,
                }
            )
    return outputs


def _visible_messages(messages):
    visible = []
    for message in messages:
        role = message.get("role")
        if role in {"human", "user"}:
            visible.append({"role": "user", "content": message.get("content", "")})
        elif role in {"ai", "assistant"} and not message.get("tool_calls"):
            visible.append({"role": "assistant", "content": message.get("content", "")})
    return visible


def main():
    host = "127.0.0.1"
    port = 8765
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
