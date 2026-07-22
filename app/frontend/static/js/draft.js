import { renderMasteryEditor } from "./masteries.js";
import { api, emptyMasteries, escapeHtml, option, showNotice, titleCase, uiState } from "./global.js";

export function renderDraftOrder() {
    const container = document.getElementById("draft-order");
    const steps = uiState.orderBuffer === null ? uiState.draftOrder : uiState.orderBuffer;
    const editing = uiState.orderBuffer !== null;
    container.innerHTML = `
    <div class="order-list">${steps.map(renderOrderStep).join("") || '<span class="muted">No actions added yet.</span>'}</div>
    ${editing ? `
      <div class="order-builder">
        <button data-add="blue,Pick">🔵 Blue Pick</button>
        <button data-add="blue,Ban">🔵 Blue Ban</button>
        <button data-add="red,Pick">🔴 Red Pick</button>
        <button data-add="red,Ban">🔴 Red Ban</button>
        <button class="secondary" id="order-undo">Undo</button>
        <button class="secondary" id="order-clear">Clear</button>
        <button class="secondary" id="order-cancel">Cancel</button>
        <button id="order-save">Save</button>
      </div>` : '<button id="order-edit">Set draft order</button>'}`;

    if (!editing) {
        document.getElementById("order-edit").onclick = () => {
            uiState.orderBuffer = [...uiState.draftOrder];
            renderDraftOrder();
        };
        return;
    }

    container.querySelectorAll("[data-add]").forEach((button) => {
        button.onclick = () => {
            uiState.orderBuffer.push(button.dataset.add.split(","));
            renderDraftOrder();
        };
    });
    document.getElementById("order-undo").onclick = () => {
        uiState.orderBuffer.pop();
        renderDraftOrder();
    };
    document.getElementById("order-clear").onclick = () => {
        uiState.orderBuffer = [];
        renderDraftOrder();
    };
    document.getElementById("order-cancel").onclick = () => {
        uiState.orderBuffer = null;
        renderDraftOrder();
    };
    document.getElementById("order-save").onclick = async () => {
        const result = await api("/api/draft-order", {
            method: "PUT",
            body: JSON.stringify({ steps: uiState.orderBuffer }),
        });
        if (!result) return;
        uiState.draftOrder = result.draft_order;
        uiState.orderBuffer = null;
        renderDraftOrder();
        showNotice("Draft order saved.");
    };
}

function renderOrderStep([side, action]) {
    return `<span class="order-step">${side === "blue" ? "🔵" : "🔴"} ${side} ${action}</span>`;
}

export function renderDraft() {
    const container = document.getElementById("draft-content");
    if (!uiState.draft) {
        container.innerHTML = `
      <p>Enter as much of T2's known hero mastery as you have.</p>
      <div id="setup-t2-editor"></div>
      <p id="confirmed-t2" class="muted"></p>
      <div class="row">
        <label>Player side<select id="player-side">
          <option value="blue">🔵 Blue</option>
          <option value="red">🔴 Red</option>
        </select></label>
        <button id="start-draft">Confirm T2 and start draft</button>
      </div>`;
        renderMasteryEditor("setup-t2-editor", "t2", { onSave: renderConfirmedT2 });
        renderConfirmedT2();
        document.getElementById("start-draft").onclick = async () => {
            uiState.draft = await api("/api/draft/start", {
                method: "POST",
                body: JSON.stringify({ player_side: document.getElementById("player-side").value }),
            });
            if (uiState.draft) renderDraft();
        };
        return;
    }
    renderActiveDraft(container);
}

function renderConfirmedT2() {
    const element = document.getElementById("confirmed-t2");
    if (element) element.textContent = `Confirmed positions: ${uiState.confirmedT2.join(", ") || "None"}`;
}

function renderActiveDraft(container) {
    const draft = uiState.draft;
    container.innerHTML = `
    <div class="team-picks">
      ${picksCard(`Player Picks (${draft.player_side})`, draft.player_picks)}
      <div class="card"><strong>Bans</strong><p>${draft.banned.map(escapeHtml).join(", ") || "No bans yet."}</p></div>
      ${picksCard("CPU Picks", draft.cpu_picks)}
    </div>
    <div id="draft-turn"></div>
    <details>
      <summary>Update known T2 masteries</summary>
      <div id="active-t2-editor"></div>
      <button id="apply-t2">Apply T2 knowledge to draft</button>
    </details>
    <button class="danger" id="end-draft">End draft</button>`;

    const turnContainer = document.getElementById("draft-turn");
    if (draft.complete) {
        turnContainer.innerHTML = '<div class="turn"><strong>Draft complete.</strong></div>';
    } else {
        const turn = draft.turn;
        turnContainer.innerHTML = `
      <div class="turn">
        <strong>Step ${draft.current_step + 1} of ${draft.total_steps}</strong><br>
        ${turn.side === "blue" ? "🔵" : "🔴"} ${turn.side} —
        ${turn.is_player ? "Player" : "CPU"} ${turn.action}
      </div>
      ${renderRecommendation(draft.recommendation, turn.action)}
      <div class="hero-toolbar">
        ${turn.action === "Pick" ? `<label>Position<select id="draft-position">
          ${uiState.positions.map((position) => option(position, position === draft.recommendation?.position)).join("")}
        </select></label>` : ""}
        <label>Filter heroes<input id="draft-search" placeholder="Type a hero name..."></label>
      </div>
      <div id="draft-heroes" class="hero-grid"></div>`;
        bindDraftHeroControls();
    }

    renderMasteryEditor("active-t2-editor", "t2");
    document.getElementById("apply-t2").onclick = async () => {
        uiState.draft = await api("/api/draft/apply-t2", { method: "POST" });
        if (uiState.draft) renderDraft();
    };
    document.getElementById("end-draft").onclick = async () => {
        const result = await api("/api/draft", { method: "DELETE" });
        if (!result) return;
        uiState.draft = null;
        uiState.t2Masteries = emptyMasteries();
        uiState.confirmedT2 = [];
        renderDraft();
    };
}

function renderRecommendation(recommendation, action) {
    if (!recommendation) return "";
    const reasons = Object.entries(recommendation.explanation || {}).map(([reason, values]) => {
        return `<div class="reason"><strong>${titleCase(reason)}:</strong> ${values.map(escapeHtml).join(", ")}</div>`;
    }).join("");
    const candidates = recommendation.candidates.map((candidate) => {
        return `<div>${escapeHtml(candidate.hero)}: ${candidate.score.toFixed(2)}</div>`;
    }).join("");
    return `
    <div class="card recommendation">
      <span class="muted">${action} recommendation</span><br>
      <strong>${escapeHtml(recommendation.hero)}</strong>
      <span> · ${escapeHtml(recommendation.position)} · ${recommendation.score.toFixed(2)}</span>
      <p>${escapeHtml(recommendation.analysis)}</p>
      ${reasons}
      <details><summary>All candidate scores</summary>${candidates}</details>
    </div>`;
}

function bindDraftHeroControls() {
    const position = document.getElementById("draft-position");
    const search = document.getElementById("draft-search");
    const turn = uiState.draft.turn;

    function renderHeroes() {
        const heroes = turn.action === "Pick" ? turn.available[position.value] || [] : turn.available.all || [];
        const query = search.value.toLowerCase();
        document.getElementById("draft-heroes").innerHTML = heroes
            .filter((hero) => hero.toLowerCase().includes(query))
            .map((hero) => `<button data-hero="${escapeHtml(hero)}">${escapeHtml(hero)}</button>`)
            .join("");
        document.querySelectorAll("#draft-heroes button").forEach((button) => {
            button.onclick = async () => {
                button.disabled = true;
                uiState.draft = await api("/api/draft/action", {
                    method: "POST",
                    body: JSON.stringify({ hero: button.dataset.hero, position: position ? position.value : null }),
                });
                if (uiState.draft) renderDraft();
            };
        });
    }

    if (position) position.addEventListener("change", renderHeroes);
    search.addEventListener("input", renderHeroes);
    renderHeroes();
}

function picksCard(title, picks) {
    const rows = Object.entries(picks).map(([hero, positions]) => {
        return `<div>${escapeHtml(hero)}: <span class="muted">${positions.join(", ")}</span></div>`;
    }).join("");
    return `<div class="card"><strong>${escapeHtml(title)}</strong><p>${rows || "No picks yet."}</p></div>`;
}
