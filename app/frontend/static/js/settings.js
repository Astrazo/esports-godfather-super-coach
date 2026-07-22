import { api, escapeHtml, modelProviders, showNotice, uiState } from "./global.js";
import { setCoachEnabled } from "./coach.js";

export function bindModelSettings() {
    const providerSelect = document.getElementById("model-provider");
    providerSelect.addEventListener("change", () => {
        const provider = modelProviders[providerSelect.value];
        if (provider) document.getElementById("model-name").value = provider.defaultModel;
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

        uiState.ai = result;
        document.getElementById("model-api-key").value = "";
        renderModelStatus();
        renderModelSettings();
        showNotice(result.enabled ? "Language model enabled." : "Graph-only mode enabled.");
    });
}

export function renderModelStatus() {
    const element = document.getElementById("ai-status");
    if (uiState.ai.enabled) {
        element.innerHTML = `<span class="dot">●</span> AI: ${escapeHtml(uiState.ai.model)}`;
    } else {
        element.textContent = "Graph-only mode";
    }
    setCoachEnabled(uiState.ai.enabled);
}

export function renderModelSettings() {
    document.getElementById("model-provider").value = uiState.ai.provider || "";
    document.getElementById("model-name").value = uiState.ai.model || "";
    document.getElementById("model-base-url").value = uiState.ai.base_url || "";
    updateModelFields();
}

function updateModelFields() {
    const providerName = document.getElementById("model-provider").value;
    const provider = modelProviders[providerName];
    const disabled = !provider;
    document.getElementById("model-name").disabled = disabled;
    document.getElementById("base-url-field").classList.toggle("hidden", disabled || !provider?.supportsBaseUrl);
    document.getElementById("api-key-field").classList.toggle("hidden", disabled || providerName === "ollama");

    let help = disabled ? "No language model will be called." : provider.help;
    if (providerName !== "ollama" && uiState.ai.api_key_configured) {
        help += " A key is currently configured for this run.";
    }
    document.getElementById("model-help").textContent = help;
}
