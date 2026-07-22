export const uiState = {
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

export const relationshipLabels = {
    synergy: "Synergies",
    counter: "Counters",
    countered_by: "Countered by",
    anti_synergy: "Anti-synergies",
};

export const modelProviders = {
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

export async function api(path, options = {}) {
    // The single browser-to-Python gateway. All API calls pass through here.
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

export function showNotice(message, isError = false) {
    const element = document.getElementById("notice");
    element.textContent = message;
    element.classList.toggle("error", isError);
    element.classList.remove("hidden");
    window.setTimeout(() => element.classList.add("hidden"), 4000);
}

export function option(value, selected = false) {
    return `<option value="${escapeHtml(value)}" ${selected ? "selected" : ""}>${escapeHtml(value)}</option>`;
}

export function titleCase(value) {
    return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = String(value);
    return element.innerHTML;
}

export function emptyMasteries() {
    const result = {};
    for (const [hero, positions] of Object.entries(uiState.t2Masteries)) {
        result[hero] = Object.fromEntries(Object.keys(positions).map((position) => [position, 0]));
    }
    return result;
}
