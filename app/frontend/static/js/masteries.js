import { api, escapeHtml, option, showNotice, uiState } from "./global.js";

export function renderMasteryEditor(containerId, team, options = {}) {
    const container = document.getElementById(containerId);
    const masteries = team === "t1" ? uiState.t1Masteries : uiState.t2Masteries;
    const initialPosition = options.position || uiState.positions[0];

    container.innerHTML = `
    <div class="mastery-controls">
      <label>Position<select class="mastery-position">
        ${uiState.positions.map((position) => option(position, position === initialPosition)).join("")}
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
        const heroes = uiState.heroes.filter((hero) => {
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
            uiState.t1Masteries = result.masteries;
        } else {
            uiState.t2Masteries = result.masteries;
            uiState.confirmedT2 = result.confirmed_t2_positions;
        }
        showNotice(`${position} masteries saved.`);

        const currentIndex = uiState.positions.indexOf(position);
        if (team === "t2" && currentIndex < uiState.positions.length - 1) {
            positionSelect.value = uiState.positions[currentIndex + 1];
            searchInput.value = "";
        }
        renderFields();
        if (options.onSave) options.onSave();
    });

    renderFields();
}
