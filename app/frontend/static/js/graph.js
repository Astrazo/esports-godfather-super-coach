import { api, escapeHtml, option, relationshipLabels, uiState } from "./global.js";

export function initialiseGraph() {
    const heroSelect = document.getElementById("graph-hero");
    heroSelect.innerHTML = uiState.heroes.map((hero) => option(hero)).join("");
    const typeContainer = document.getElementById("graph-types");
    typeContainer.innerHTML = Object.entries(relationshipLabels).map(([value, label]) => `
    <label><input type="checkbox" value="${value}" checked> ${label}</label>`).join("");
    heroSelect.addEventListener("change", renderGraph);
    typeContainer.addEventListener("change", renderGraph);
    renderGraph();
}

async function renderGraph() {
    const hero = document.getElementById("graph-hero").value;
    const types = [...document.querySelectorAll("#graph-types input:checked")].map((input) => input.value);
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
        return { ...target, left: 50 + Math.cos(angle) * 38, top: 50 + Math.sin(angle) * 38 };
    });
    const lines = positionedTargets.map((target) => `
    <line class="graph-edge ${target.type}" x1="50" y1="50" x2="${target.left}" y2="${target.top}"></line>`).join("");

    canvas.innerHTML = `
    <svg class="graph-edges" viewBox="0 0 100 100" preserveAspectRatio="none">${lines}</svg>
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
