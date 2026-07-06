const state = {
  positions: [],
  heroes: [],
  t1Masteries: {},
  t2Masteries: {},
  confirmedT2: [],
  draftOrder: [],
  draft: null,
  ai: {},
  orderBuffer: null,
};

const relationshipLabels = {
  synergy: "Synergies",
  counter: "Counters",
  countered_by: "Countered by",
  anti_synergy: "Anti-synergies",
};

const modelProviders = {
  ollama: {
    defaultModel: "qwen3.5",
    supportsBaseUrl: true,
    help: "Ollama runs locally and does not require an API key.",
  },
  openai: {
    defaultModel: "gpt-5-mini",
    supportsBaseUrl: true,
    help: "Requires an OpenAI API key, or the OPENAI_API_KEY environment variable.",
  },
  anthropic: {
    defaultModel: "claude-sonnet-4-6",
    supportsBaseUrl: false,
    help: "Requires an Anthropic API key, or the ANTHROPIC_API_KEY environment variable.",
  },
  google_genai: {
    defaultModel: "gemini-2.5-flash",
    supportsBaseUrl: false,
    help: "Requires a Google AI key, or the GOOGLE_API_KEY environment variable.",
  },
};

document.addEventListener("DOMContentLoaded", initialise);

async function initialise() {
  bindNavigation();
  bindCoach();
  bindModelSettings();
  const data = await api("/api/bootstrap");
  state.positions = data.positions;
  state.heroes = data.heroes;
  state.t1Masteries = data.t1_masteries;
  state.t2Masteries = data.t2_masteries;
  state.confirmedT2 = data.confirmed_t2_positions;
  state.draftOrder = data.draft_order;
  state.draft = data.draft;
  state.ai = data.ai;

  renderAiStatus();
  renderModelSettings();
  renderCoach(data.coach_messages);
  renderMasteryEditor("team-editor", "t1");
  initialiseGraph();
  renderDraftOrder();
  renderDraft();
}

function bindNavigation() {
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

function renderAiStatus() {
  const element = document.getElementById("ai-status");
  if (state.ai.enabled) {
    element.innerHTML = `<span class="dot">●</span> AI: ${escapeHtml(state.ai.model)}`;
    document.getElementById("coach-input").disabled = false;
    document.getElementById("coach-input").placeholder = "What are your thoughts on Babe?";
  } else {
    element.textContent = "Graph-only mode";
    document.getElementById("coach-input").disabled = true;
    document.getElementById("coach-input").placeholder = "Configure LEG_AI_MODEL to enable coach chat.";
  }
}

function bindModelSettings() {
  const providerSelect = document.getElementById("model-provider");
  providerSelect.addEventListener("change", () => {
    const provider = modelProviders[providerSelect.value];
    if (provider) {
      document.getElementById("model-name").value = provider.defaultModel;
    }
    updateModelFields();
  });

  document.getElementById("model-settings").addEventListener("submit", async (event) => {
    event.preventDefault();
    const result = await api("/api/settings/model", {
      method: "PUT",
      body: JSON.stringify({
        provider: providerSelect.value,
        model: document.getElementById("model-name").value,
        base_url: document.getElementById("model-base-url").value,
        api_key: document.getElementById("model-api-key").value,
      }),
    });
    if (!result) return;

    state.ai = result;
    document.getElementById("model-api-key").value = "";
    renderAiStatus();
    renderModelSettings();
    showNotice(result.enabled ? "Language model enabled." : "Graph-only mode enabled.");
  });
}

function renderModelSettings() {
  document.getElementById("model-provider").value = state.ai.provider || "";
  document.getElementById("model-name").value = state.ai.model || "";
  document.getElementById("model-base-url").value = state.ai.base_url || "";
  updateModelFields();
}

function updateModelFields() {
  const providerName = document.getElementById("model-provider").value;
  const provider = modelProviders[providerName];
  const disabled = !provider;
  document.getElementById("model-name").disabled = disabled;
  document.getElementById("base-url-field").classList.toggle(
    "hidden",
    disabled || !provider?.supportsBaseUrl,
  );
  document.getElementById("api-key-field").classList.toggle(
    "hidden",
    disabled || providerName === "ollama",
  );

  let help = disabled ? "No language model will be called." : provider.help;
  if (providerName !== "ollama" && state.ai.api_key_configured) {
    help += " A key is currently configured for this run.";
  }
  document.getElementById("model-help").textContent = help;
}

function renderMasteryEditor(containerId, team, options = {}) {
  const container = document.getElementById(containerId);
  const masteries = team === "t1" ? state.t1Masteries : state.t2Masteries;
  const initialPosition = options.position || state.positions[0];

  container.innerHTML = `
    <div class="mastery-controls">
      <label>Position<select class="mastery-position">
        ${state.positions.map((position) => option(position, position === initialPosition)).join("")}
      </select></label>
      <label>Filter heroes<input class="mastery-search" placeholder="Type a hero name..."></label>
    </div>
    <form class="mastery-form">
      <div class="mastery-grid"></div>
      <div class="mastery-actions">
        <button type="submit">${team === "t1" ? "Save masteries" : "Confirm position masteries"}</button>
      </div>
    </form>`;

  const positionSelect = container.querySelector(".mastery-position");
  const searchInput = container.querySelector(".mastery-search");
  const form = container.querySelector(".mastery-form");

  function renderFields() {
    const position = positionSelect.value;
    const search = searchInput.value.toLowerCase();
    const heroes = state.heroes.filter((hero) => {
      return position in (masteries[hero] || {}) && hero.toLowerCase().includes(search);
    });
    form.querySelector(".mastery-grid").innerHTML = heroes.map((hero) => `
      <label class="mastery-item">
        <span>${escapeHtml(hero)}</span>
        <input type="number" min="0" max="7" name="${escapeHtml(hero)}"
          value="${masteries[hero][position]}">
      </label>`).join("");
  }

  positionSelect.addEventListener("change", renderFields);
  searchInput.addEventListener("input", renderFields);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const position = positionSelect.value;
    const levels = {};
    form.querySelectorAll("input[type=number]").forEach((input) => {
      levels[input.name] = Number(input.value);
    });
    const result = await api(`/api/masteries/${team}`, {
      method: "PUT",
      body: JSON.stringify({ position, levels }),
    });
    if (!result) return;

    if (team === "t1") {
      state.t1Masteries = result.masteries;
    } else {
      state.t2Masteries = result.masteries;
      state.confirmedT2 = result.confirmed_t2_positions;
    }
    showNotice(`${position} masteries saved.`);

    const currentIndex = state.positions.indexOf(position);
    if (team === "t2" && currentIndex < state.positions.length - 1) {
      positionSelect.value = state.positions[currentIndex + 1];
      searchInput.value = "";
    }
    renderFields();
    if (options.onSave) options.onSave();
  });

  renderFields();
}

function initialiseGraph() {
  const heroSelect = document.getElementById("graph-hero");
  heroSelect.innerHTML = state.heroes.map((hero) => option(hero)).join("");
  const typeContainer = document.getElementById("graph-types");
  typeContainer.innerHTML = Object.entries(relationshipLabels).map(([value, label]) => `
    <label><input type="checkbox" value="${value}" checked> ${label}</label>`).join("");
  heroSelect.addEventListener("change", renderGraph);
  typeContainer.addEventListener("change", renderGraph);
  renderGraph();
}

async function renderGraph() {
  const hero = document.getElementById("graph-hero").value;
  const types = [...document.querySelectorAll("#graph-types input:checked")]
    .map((input) => input.value);
  const query = types.map((type) => `relationship_type=${encodeURIComponent(type)}`).join("&");
  const result = await api(`/api/graph/${encodeURIComponent(hero)}?${query}`);
  if (!result) return;

  const canvas = document.getElementById("graph-canvas");
  const targets = [];
  Object.entries(result.relationships).forEach(([type, heroes]) => {
    heroes.forEach((target) => targets.push({ type, hero: target }));
  });

  const positionedTargets = targets.map((target, index) => {
    const angle = (index / Math.max(targets.length, 1)) * Math.PI * 2;
    return {
      ...target,
      left: 50 + Math.cos(angle) * 38,
      top: 50 + Math.sin(angle) * 38,
    };
  });

  const lines = positionedTargets.map((target) => `
    <line
      class="graph-edge ${target.type}"
      x1="50"
      y1="50"
      x2="${target.left}"
      y2="${target.top}">
    </line>`).join("");

  canvas.innerHTML = `
    <svg class="graph-edges" viewBox="0 0 100 100" preserveAspectRatio="none">
      ${lines}
    </svg>
    <div class="graph-node focus" style="left:50%;top:50%">${escapeHtml(hero)}</div>`;

  positionedTargets.forEach((target) => {
    canvas.insertAdjacentHTML(
      "beforeend",
      `<div class="graph-node" title="${relationshipLabels[target.type]}"
        style="left:${target.left}%;top:${target.top}%">${escapeHtml(target.hero)}</div>`,
    );
  });

  const details = document.getElementById("graph-details");
  details.innerHTML = Object.entries(relationshipLabels).map(([type, label]) => {
    const heroes = result.relationships[type] || [];
    return heroes.length
      ? `<div class="relationship-list"><strong>${label}:</strong> ${heroes.map(escapeHtml).join(", ")}</div>`
      : "";
  }).join("") || '<span class="muted">No matching outgoing relationships.</span>';
}

function renderDraftOrder() {
  const container = document.getElementById("draft-order");
  const steps = state.orderBuffer === null ? state.draftOrder : state.orderBuffer;
  const editing = state.orderBuffer !== null;
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
      state.orderBuffer = [...state.draftOrder];
      renderDraftOrder();
    };
    return;
  }

  container.querySelectorAll("[data-add]").forEach((button) => {
    button.onclick = () => {
      state.orderBuffer.push(button.dataset.add.split(","));
      renderDraftOrder();
    };
  });
  document.getElementById("order-undo").onclick = () => {
    state.orderBuffer.pop();
    renderDraftOrder();
  };
  document.getElementById("order-clear").onclick = () => {
    state.orderBuffer = [];
    renderDraftOrder();
  };
  document.getElementById("order-cancel").onclick = () => {
    state.orderBuffer = null;
    renderDraftOrder();
  };
  document.getElementById("order-save").onclick = async () => {
    const result = await api("/api/draft-order", {
      method: "PUT",
      body: JSON.stringify({ steps: state.orderBuffer }),
    });
    if (!result) return;
    state.draftOrder = result.draft_order;
    state.orderBuffer = null;
    renderDraftOrder();
    showNotice("Draft order saved.");
  };
}

function renderOrderStep([side, action]) {
  return `<span class="order-step">${side === "blue" ? "🔵" : "🔴"} ${side} ${action}</span>`;
}

function renderDraft() {
  const container = document.getElementById("draft-content");
  if (!state.draft) {
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
      state.draft = await api("/api/draft/start", {
        method: "POST",
        body: JSON.stringify({ player_side: document.getElementById("player-side").value }),
      });
      if (state.draft) renderDraft();
    };
    return;
  }
  renderActiveDraft(container);
}

function renderConfirmedT2() {
  const element = document.getElementById("confirmed-t2");
  if (element) {
    element.textContent = `Confirmed positions: ${state.confirmedT2.join(", ") || "None"}`;
  }
}

function renderActiveDraft(container) {
  const draft = state.draft;
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
          ${state.positions.map((position) => option(
            position,
            position === draft.recommendation?.position,
          )).join("")}
        </select></label>` : ""}
        <label>Filter heroes<input id="draft-search" placeholder="Type a hero name..."></label>
      </div>
      <div id="draft-heroes" class="hero-grid"></div>`;
    bindDraftHeroControls();
  }

  renderMasteryEditor("active-t2-editor", "t2");
  document.getElementById("apply-t2").onclick = async () => {
    state.draft = await api("/api/draft/apply-t2", { method: "POST" });
    if (state.draft) renderDraft();
  };
  document.getElementById("end-draft").onclick = async () => {
    const result = await api("/api/draft", { method: "DELETE" });
    if (!result) return;
    state.draft = null;
    state.t2Masteries = emptyMasteries();
    state.confirmedT2 = [];
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
  const turn = state.draft.turn;

  function renderHeroes() {
    const heroes = turn.action === "Pick"
      ? turn.available[position.value] || []
      : turn.available.all || [];
    const query = search.value.toLowerCase();
    document.getElementById("draft-heroes").innerHTML = heroes
      .filter((hero) => hero.toLowerCase().includes(query))
      .map((hero) => `<button data-hero="${escapeHtml(hero)}">${escapeHtml(hero)}</button>`)
      .join("");
    document.querySelectorAll("#draft-heroes button").forEach((button) => {
      button.onclick = async () => {
        button.disabled = true;
        state.draft = await api("/api/draft/action", {
          method: "POST",
          body: JSON.stringify({
            hero: button.dataset.hero,
            position: position ? position.value : null,
          }),
        });
        if (state.draft) renderDraft();
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

function bindCoach() {
  document.getElementById("coach-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("coach-input");
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    appendChatMessage({ role: "user", content: message });
    const result = await api("/api/coach", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    if (result) renderCoach(result.messages);
  });
  document.getElementById("clear-coach").onclick = async () => {
    const result = await api("/api/coach", { method: "DELETE" });
    if (result) renderCoach([]);
  };
}

function renderCoach(messages) {
  const container = document.getElementById("chat-messages");
  container.innerHTML = "";
  messages.forEach(appendChatMessage);
}

function appendChatMessage(message) {
  const container = document.getElementById("chat-messages");
  container.insertAdjacentHTML(
    "beforeend",
    `<div class="message ${message.role}">${escapeHtml(message.content)}</div>`,
  );
  container.scrollTop = container.scrollHeight;
}

function emptyMasteries() {
  const result = {};
  for (const [hero, positions] of Object.entries(state.t2Masteries)) {
    result[hero] = Object.fromEntries(Object.keys(positions).map((position) => [position, 0]));
  }
  return result;
}

async function api(path, options = {}) {
  const settings = {
    headers: { "Content-Type": "application/json" },
    ...options,
  };
  try {
    const response = await fetch(path, settings);
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Request failed.");
    return body;
  } catch (error) {
    showNotice(error.message, true);
    return null;
  }
}

function showNotice(message, isError = false) {
  const element = document.getElementById("notice");
  element.textContent = message;
  element.classList.toggle("error", isError);
  element.classList.remove("hidden");
  window.setTimeout(() => element.classList.add("hidden"), 4000);
}

function option(value, selected = false) {
  return `<option value="${escapeHtml(value)}" ${selected ? "selected" : ""}>${escapeHtml(value)}</option>`;
}

function titleCase(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = String(value);
  return element.innerHTML;
}
