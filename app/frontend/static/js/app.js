import "../vendor/deep-chat/deepChat.bundle.js";
import { uiState, api } from "./global.js";
import { bindCoach, renderCoach } from "./coach.js";
import { bindModelSettings, renderModelStatus, renderModelSettings } from "./settings.js";
import { renderMasteryEditor } from "./masteries.js";
import { initialiseGraph } from "./graph.js";
import { renderDraft, renderDraftOrder } from "./draft.js";

document.addEventListener("DOMContentLoaded", initialise);

// App startup: load all server state once, then build each feature from that state.
async function initialise() {
    bindNavigation();
    bindCoach();
    bindModelSettings();

    const data = await api("/api/bootstrap");
    if (!data) return;

    uiState.positions = data.positions;
    uiState.heroes = data.heroes;
    uiState.t1Masteries = data.t1_masteries;
    uiState.t2Masteries = data.t2_masteries;
    uiState.confirmedT2 = data.confirmed_t2_positions;
    uiState.draftOrder = data.draft_order;
    uiState.draft = data.draft;
    uiState.ai = data.ai;

    renderModelStatus();
    renderModelSettings();
    renderCoach(data.coach_messages);
    renderMasteryEditor("team-editor", "t1");
    initialiseGraph();
    renderDraftOrder();
    renderDraft();
}

function bindNavigation() {
    // Navigation is frontend-only: it switches the visible page and calls no API.
    document.querySelectorAll(".nav-link").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".nav-link, .page").forEach((element) => {
                element.classList.remove("active");
            });
            button.classList.add("active");
            document.getElementById(`page-${button.dataset.page}`).classList.add("active");
        });
    });
}
