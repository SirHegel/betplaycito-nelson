(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const numberFormatter = new Intl.NumberFormat("es-CO");
  const percentFormatter = new Intl.NumberFormat("es-CO", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const dateFormatter = new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const PREVIEW_MODE = window.location.protocol === "file:";

  const VIEW_TITLES = {
    dashboard: "Resumen general",
    history: "Historial",
    backups: "Datos y respaldos",
    settings: "Seguridad",
    help: "Ayuda",
  };

  const COLOR_SETS = {
    result: ["#b9f44a", "#ffc857", "#a88bff"],
    goals: ["#35d9e6", "#ff7d6b"],
    btts: ["#b9f44a", "#a88bff"],
    local: ["#35d9e6", "#ff7d6b"],
    corners: ["#a88bff", "#ffc857"],
    shots: ["#ff7d6b", "#35d9e6"],
    totalShots: ["#afff6a", "#a995ff"],
    targetRange: ["#58d5df", "#ff816d"],
    cornersRange: ["#ffd16c", "#a995ff"],
    cards: ["#ff816d", "#ffd16c"],
    halves: ["#afff6a", "#58d5df", "#a995ff"],
    fallback: ["#b9f44a", "#35d9e6", "#a88bff", "#ff7d6b"],
  };

  const GROUP_HELP = {
    result: "Compara cuántos registros terminaron con victoria local, empate o victoria visitante.",
    goals: "Más de 2.5 significa 3 goles o más; menos de 2.5 significa entre 0 y 2.",
    btts: "Gol/Gol indica que ambos equipos marcaron al menos una vez.",
    local: "Indica si el equipo local logró marcar al menos un gol.",
    corners: "Más de 9.5 corresponde a 10 o más córners totales; menos, entre 0 y 9.",
    shots: "Más de 9.5 corresponde a 10 o más tiros al arco totales; menos, entre 0 y 9.",
    totalShots: "+25,5 registra la condición de más de 25,5 remates; −26,5 registra la condición de menos de 26,5.",
    targetRange: "+7,5 registra la condición de más de 7,5 tiros a puerta; −8,5 registra la condición de menos de 8,5.",
    cornersRange: "+9,5 registra la condición de más de 9,5 tiros de esquina; −10,5 registra la condición de menos de 10,5.",
    cards: "+4 registra la condición de más de 4 tarjetas; −5 registra la condición de menos de 5.",
    halves: "+0,5 1M significa que la primera mitad tuvo al menos un gol más que la segunda; +0,5 2M, que la segunda tuvo al menos uno más; == significa que ambas tuvieron la misma cantidad.",
  };

  const PREVIEW_GROUPS = [
    { key: "result", label: "Resultado del partido", categories: ["home_win", "draw", "away_win"] },
    { key: "goals", label: "Total de goles 2.5", categories: ["over25", "under25"] },
    { key: "btts", label: "Ambos equipos marcan", categories: ["btts_yes", "btts_no"] },
    { key: "local_goal", label: "Marcador local", categories: ["local_scored", "local_blank"] },
    { key: "corners", label: "Tiros de esquina 9.5", categories: ["corners_over95", "corners_under95"] },
    { key: "shots_on_target", label: "Tiros al arco 9.5", categories: ["shots_over95", "shots_under95"] },
    { key: "total_shots_range", label: "Remates totales", categories: ["total_shots_over255", "total_shots_under265"] },
    { key: "shots_on_target_range", label: "Tiros a puerta", categories: ["shots_on_target_over75", "shots_on_target_under85"] },
    { key: "corners_range", label: "Tiros de esquina", categories: ["corners_plus95", "corners_minus105"] },
    { key: "cards_range", label: "Tarjetas", categories: ["cards_plus4", "cards_minus5"] },
    { key: "half_goals", label: "Goles por mitades", categories: ["first_half_more_goals", "second_half_more_goals", "halves_equal_goals"] },
  ];

  const PREVIEW_LABELS = {
    home_win: "Ganó el local",
    draw: "Empate",
    away_win: "Ganó el visitante",
    over25: "Más de 2.5 goles",
    under25: "Menos de 2.5 goles",
    btts_yes: "Gol / Gol",
    btts_no: "No Gol / Gol",
    local_scored: "Local marcó",
    local_blank: "Local no marcó",
    corners_over95: "Más de 9.5 tiros de esquina",
    corners_under95: "Menos de 9.5 tiros de esquina",
    shots_over95: "Más de 9.5 tiros al arco",
    shots_under95: "Menos de 9.5 tiros al arco",
    total_shots_over255: "+25,5 remates",
    total_shots_under265: "−26,5 remates",
    shots_on_target_over75: "+7,5 tiros a puerta",
    shots_on_target_under85: "−8,5 tiros a puerta",
    corners_plus95: "+9,5 tiros de esquina",
    corners_minus105: "−10,5 tiros de esquina",
    cards_plus4: "+4 tarjetas",
    cards_minus5: "−5 tarjetas",
    first_half_more_goals: "+0,5 · 1M",
    second_half_more_goals: "+0,5 · 2M",
    halves_equal_goals: "== · mismas cantidades",
  };

  const PREVIEW_TEAMS = [];
  const PREVIEW_HISTORY = [];

  const PREVIEW_STATE = {
    authenticated: true,
    setup_required: false,
    user: { id: 1, username: "Administrador" },
    features: { teams: false, matches: false, backups: false, restore: false, xlsx: false, shutdown: false, persistent_sqlite: false },
    variables: PREVIEW_GROUPS.flatMap((group) => group.categories.map((key) => ({
      key,
      group: group.key,
      label: PREVIEW_LABELS[key],
      alternatives: group.categories.filter((candidate) => candidate !== key),
    }))),
    groups: PREVIEW_GROUPS,
    version: "vista-vacía",
  };

  const state = {
    user: null,
    features: {},
    variables: [],
    groupDefinitions: [],
    teams: [],
    selectedTeamIds: new Set(),
    dashboard: null,
    comparisonDashboards: new Map(),
    selectedCategories: new Map(),
    activeMetricGroupKey: null,
    activeView: "dashboard",
    entryTeamId: "",
    history: { items: [], page: 1, page_size: 25, total: 0, total_pages: 1 },
    historyPage: 1,
    restorePayload: null,
    pendingRequests: 0,
  };

  class ApiError extends Error {
    constructor(message, status = 0, code = "request_failed", fields = null) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code;
      this.fields = fields;
    }
  }

  function previewDashboard(teamIds = []) {
    const groups = PREVIEW_GROUPS.map((definition) => {
      return {
        key: definition.key,
        label: definition.label,
        total: 0,
        categories: definition.categories.map((key) => ({
          key,
          label: PREVIEW_LABELS[key],
          count: 0,
          percentage: 0,
          manual_count: 0,
          match_count: 0,
          decrementable_count: 0,
          can_decrement: false,
        })),
      };
    });
    return {
      groups,
      totals: {
        observations: 0,
        adjustments: 0,
        adjustment_units: 0,
        matches: 0,
      },
    };
  }

  async function previewApi(path, options = {}) {
    await Promise.resolve();
    const method = String(options.method || "GET").toUpperCase();
    if (method !== "GET") {
      throw new ApiError(
        "Esta vista está vacía y es de solo lectura. Abre la aplicación instalada para guardar tus datos.",
        0,
        "preview_read_only"
      );
    }
    const url = new URL(path, "file:///");
    if (url.pathname === "/api/setup/status") return { setup_required: false };
    if (url.pathname === "/api/state") return structuredClone(PREVIEW_STATE);
    if (url.pathname === "/api/teams") return structuredClone(PREVIEW_TEAMS);
    if (url.pathname === "/api/dashboard") {
      const ids = (url.searchParams.get("team_ids") || "")
        .split(",")
        .map(Number)
        .filter((value) => Number.isInteger(value) && PREVIEW_TEAMS.some((team) => team.id === value));
      return previewDashboard(ids);
    }
    if (url.pathname === "/api/history") {
      return {
        items: structuredClone(PREVIEW_HISTORY),
        page: 1,
        page_size: 25,
        total: PREVIEW_HISTORY.length,
        total_pages: 1,
      };
    }
    throw new ApiError("Esta acción no está disponible en la vista previa vacía.", 0, "preview_unavailable");
  }

  async function api(path, options = {}) {
    if (PREVIEW_MODE) return previewApi(path, options);
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    let body = options.body;

    if (body !== undefined && body !== null && !(body instanceof FormData) && typeof body !== "string") {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(path, {
        ...options,
        body,
        headers,
        credentials: "same-origin",
      });
    } catch (error) {
      throw new ApiError("No fue posible conectar con el aplicativo. Verifica que esté abierto.", 0, "offline");
    }

    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      if (!response.ok) {
        throw new ApiError(`La solicitud falló (${response.status}).`, response.status);
      }
      return response;
    }

    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new ApiError("El aplicativo devolvió una respuesta inválida.", response.status, "invalid_response");
    }

    if (!response.ok || payload?.ok === false) {
      const detail = payload?.error || {};
      throw new ApiError(detail.message || "No se pudo completar la operación.", response.status, detail.code, detail.fields);
    }

    return Object.prototype.hasOwnProperty.call(payload || {}, "data") ? payload.data : payload;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatCount(value) {
    const number = Number(value);
    return numberFormatter.format(Number.isFinite(number) ? number : 0);
  }

  function formatPercent(value) {
    const number = Number(value);
    return `${percentFormatter.format(Number.isFinite(number) ? number : 0)} %`;
  }

  function setAnimatedCount(element, value) {
    const target = Math.max(0, Number(value) || 0);
    const previous = Number(element.dataset.numericValue) || 0;
    element.dataset.numericValue = String(target);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || previous === target) {
      element.textContent = formatCount(target);
      return;
    }
    const started = performance.now();
    const duration = 720;
    const tick = (now) => {
      if (Number(element.dataset.numericValue) !== target) return;
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = formatCount(Math.round(previous + (target - previous) * eased));
      if (progress < 1) window.requestAnimationFrame(tick);
    };
    window.requestAnimationFrame(tick);
  }

  function safeDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : dateFormatter.format(date);
  }

  function initials(name) {
    const parts = String(name || "A").trim().split(/\s+/).filter(Boolean);
    return parts.slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "A";
  }

  function setBusy(button, busy, busyLabel = "Guardando…") {
    if (!button) return;
    if (busy) {
      button.dataset.originalLabel = button.innerHTML;
      button.disabled = true;
      button.textContent = busyLabel;
    } else {
      button.disabled = false;
      if (button.dataset.originalLabel) button.innerHTML = button.dataset.originalLabel;
      delete button.dataset.originalLabel;
    }
  }

  function setSaveStatus(kind, text) {
    const element = $("#save-status");
    element.classList.toggle("is-saved", kind === "saved");
    element.classList.toggle("is-error", kind === "error");
    $("span", element).textContent = text;
  }

  function requestStarted() {
    state.pendingRequests += 1;
    setSaveStatus("pending", "Guardando…");
  }

  function requestFinished(success = true) {
    state.pendingRequests = Math.max(0, state.pendingRequests - 1);
    if (state.pendingRequests === 0) {
      setSaveStatus(success ? "saved" : "error", success ? "Todo guardado" : "Error al guardar");
    }
  }

  function showToast(title, message = "", options = {}) {
    const toast = document.createElement("div");
    toast.className = `toast${options.error ? " toast--error" : ""}`;
    toast.setAttribute("role", options.error ? "alert" : "status");
    toast.innerHTML = `
      <span class="toast__mark" aria-hidden="true">${options.error ? "!" : "✓"}</span>
      <div><strong>${escapeHtml(title)}</strong>${message ? `<span>${escapeHtml(message)}</span>` : ""}</div>
    `;

    if (options.actionLabel && typeof options.onAction === "function") {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = options.actionLabel;
      button.addEventListener("click", async () => {
        button.disabled = true;
        await options.onAction();
        toast.remove();
      }, { once: true });
      toast.append(button);
    }

    $("#toast-region").append(toast);
    window.setTimeout(() => toast.remove(), options.duration || 5500);
  }

  function showFormError(element, message) {
    element.textContent = message;
    element.hidden = !message;
  }

  function showAuth(mode = "login", error = "") {
    $("#auth-screen").hidden = false;
    $("#app-shell").hidden = true;
    const setup = mode === "setup";
    $("#login-form").hidden = setup;
    $("#setup-form").hidden = !setup;
    $("#auth-title").textContent = setup ? "Crear administrador" : "Iniciar sesión";
    $("#auth-subtitle").textContent = setup
      ? "Esta instalación todavía no tiene una cuenta configurada."
      : "Ingresa con tu cuenta de administrador.";
    showFormError(setup ? $("#setup-error") : $("#login-error"), error);
    window.setTimeout(() => $(setup ? "#setup-form input" : "#login-username")?.focus(), 30);
  }

  function showApp() {
    $("#auth-screen").hidden = true;
    $("#app-shell").hidden = false;
  }

  async function boot() {
    bindEvents();
    if (PREVIEW_MODE) {
      document.documentElement.dataset.preview = "true";
      document.body.classList.add("is-preview");
      $("#preview-banner").hidden = false;
      await hydrateApp(structuredClone(PREVIEW_STATE));
      setSaveStatus("saved", "Solo lectura");
      window.setTimeout(() => showToast(
        "Vista vacía",
        "No hay equipos ni estadísticas precargadas. Abre el ejecutable para guardar tus datos."
      ), 650);
      return;
    }
    try {
      const setupStatus = await api("/api/setup/status");
      if (setupStatus?.setup_required) {
        showAuth("setup");
        return;
      }
    } catch (error) {
      showAuth("login", error.message);
      setSaveStatus("error", "Sin conexión");
      return;
    }

    try {
      const appState = await api("/api/state");
      if (appState?.authenticated) {
        await hydrateApp(appState);
      } else {
        showAuth("login");
      }
    } catch (error) {
      if (error.status === 401) showAuth("login");
      else showAuth("login", error.message);
    }
  }

  async function hydrateApp(appState = null) {
    const serverState = appState || await api("/api/state");
    state.user = serverState.user || { username: "Administrador" };
    state.features = serverState.features || {};
    state.variables = Array.isArray(serverState.variables) ? serverState.variables : [];
    state.groupDefinitions = Array.isArray(serverState.groups) ? serverState.groups : [];

    const username = state.user.username || "Administrador";
    $("#sidebar-username").textContent = username;
    $("#welcome-name").textContent = username;
    $("#sidebar-avatar").textContent = initials(username);
    $("#topbar-avatar").textContent = initials(username);
    applyFeatureVisibility();
    populateVariableFilters();
    showApp();
    setView("dashboard", false);
    setSaveStatus("saved", "Conectado");

    try {
      await loadTeams();
      await loadDashboard();
    } catch (error) {
      handleApiError(error, "No fue posible cargar el panel.");
    }
  }

  function applyFeatureVisibility() {
    const matchesEnabled = state.features.matches !== false;
    [$("#open-match-button"), $("#hero-match-button"), $("#mobile-match-button")].forEach((button) => {
      if (button) button.hidden = !matchesEnabled;
    });
    $("#xlsx-card").hidden = state.features.xlsx === false;
    $("#server-backup-card").hidden = state.features.backups === false;
    $("#restore-panel").hidden = state.features.restore === false;
    $("#shutdown-button").hidden = state.features.shutdown === false;
    $("#add-team-form").hidden = state.features.teams === false;
    $("#manage-teams-button").hidden = state.features.teams === false;
  }

  function setView(viewName, focus = true) {
    if (!VIEW_TITLES[viewName]) return;
    state.activeView = viewName;
    $$('[data-view-panel]').forEach((panel) => { panel.hidden = panel.dataset.viewPanel !== viewName; });
    $$('[data-view]').forEach((button) => {
      const active = button.dataset.view === viewName;
      button.classList.toggle("is-active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    $("#view-title").textContent = VIEW_TITLES[viewName];
    closeSidebar();
    if (viewName === "history") loadHistory();
    if (focus) $("#main-content").focus({ preventScroll: true });
  }

  async function handleLogin(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const values = Object.fromEntries(new FormData(form));
    showFormError($("#login-error"), "");
    setBusy(button, true, "Ingresando…");
    try {
      await api("/api/login", { method: "POST", body: values });
      form.reset();
      await hydrateApp();
    } catch (error) {
      showFormError($("#login-error"), error.message);
    } finally {
      setBusy(button, false);
    }
  }

  async function handleSetup(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const values = Object.fromEntries(new FormData(form));
    showFormError($("#setup-error"), "");
    setBusy(button, true, "Creando…");
    try {
      await api("/api/setup", { method: "POST", body: values });
      form.reset();
      showAuth("login");
      showToast("Administrador creado", "Ya puedes iniciar sesión.");
    } catch (error) {
      showFormError($("#setup-error"), error.message);
    } finally {
      setBusy(button, false);
    }
  }

  async function handleLogout() {
    if (PREVIEW_MODE) {
      showToast("Vista previa vacía", "El cierre de sesión está disponible en la aplicación instalada.");
      return;
    }
    try {
      await api("/api/logout", { method: "POST" });
    } catch (error) {
      // A local session can still be cleared visually if the process ended.
    }
    state.user = null;
    state.dashboard = null;
    state.selectedTeamIds.clear();
    showAuth("login");
  }

  async function loadTeams() {
    if (state.features.teams === false) {
      state.teams = [];
      renderTeams();
      return;
    }
    const data = await api("/api/teams?include_archived=1");
    state.teams = Array.isArray(data) ? data : (data?.items || data?.teams || []);
    const validIds = new Set(state.teams.filter((team) => !team.archived).map((team) => Number(team.id)));
    state.selectedTeamIds.forEach((id) => {
      if (!validIds.has(Number(id))) state.selectedTeamIds.delete(id);
    });
    renderTeams();
    populateMatchTeamOptions();
  }

  function renderTeams() {
    const activeTeams = state.teams.filter((team) => !team.archived);
    $("#kpi-teams").textContent = formatCount(activeTeams.length);
    const container = $("#team-chips");
    if (!activeTeams.length) {
      container.innerHTML = '<span class="team-chip-empty">No hay equipos. Puedes trabajar con estadísticas globales o crear el primero.</span>';
    } else {
      container.innerHTML = activeTeams.map((team) => `
        <label class="team-chip">
          <input type="checkbox" value="${Number(team.id)}" ${state.selectedTeamIds.has(Number(team.id)) ? "checked" : ""}>
          <span>${escapeHtml(team.name)}</span>
        </label>
      `).join("");
    }

    renderTeamManager();
    updateEntryTeamSelect();
    updateScopeCopy();
  }

  function updateEntryTeamSelect() {
    const select = $("#entry-team-select");
    const activeTeams = state.teams.filter((team) => !team.archived);
    const selectedTeams = activeTeams.filter((team) => state.selectedTeamIds.has(Number(team.id)));
    const previous = String(state.entryTeamId ?? "");
    select.innerHTML = selectedTeams.length
      ? selectedTeams.map((team) => `<option value="${Number(team.id)}">${escapeHtml(team.name)}</option>`).join("")
      : '<option value="">Global (sin equipo)</option>';

    const selectedIds = [...state.selectedTeamIds].map(String);
    let next = previous;
    if (!selectedIds.length) next = "";
    else if (!selectedIds.includes(previous)) next = selectedIds[0];
    if (![...select.options].some((option) => option.value === next)) next = "";
    select.value = next;
    state.entryTeamId = next;
    refreshAdjustmentAvailability();
  }

  function updateScopeCopy() {
    const selectedTeams = getSelectedTeams();
    const summary = $("#scope-summary");
    const kpiScope = $("#kpi-scope");
    if (!selectedTeams.length) {
      summary.innerHTML = "<strong>Vista global</strong> · incluye todos los registros.";
      kpiScope.textContent = "Vista global";
    } else {
      const names = selectedTeams.map((team) => team.name).join(", ");
      summary.innerHTML = `<strong>${selectedTeams.length === 1 ? "Vista de equipo" : "Vista agregada"}</strong> · ${escapeHtml(names)}.`;
      kpiScope.textContent = `${selectedTeams.length} seleccionado${selectedTeams.length === 1 ? "" : "s"}`;
    }
  }

  function getSelectedTeams() {
    return state.teams.filter((team) => !team.archived && state.selectedTeamIds.has(Number(team.id)));
  }

  async function handleCreateTeam(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = $("#new-team-name");
    const name = input.value.trim();
    if (!name) {
      input.focus();
      return;
    }
    const button = $('button[type="submit"]', form);
    setBusy(button, true, "Creando…");
    try {
      const created = await api("/api/teams", { method: "POST", body: { name } });
      input.value = "";
      await loadTeams();
      const team = created?.team || created;
      if (team?.id) {
        state.selectedTeamIds.add(Number(team.id));
        state.entryTeamId = String(team.id);
        renderTeams();
        await scopeChanged();
      }
      showToast("Equipo creado", `${name} ya está disponible.`);
    } catch (error) {
      handleApiError(error, "No se pudo crear el equipo.");
    } finally {
      setBusy(button, false);
    }
  }

  async function handleTeamSelection(event) {
    const checkbox = event.target.closest('input[type="checkbox"]');
    if (!checkbox) return;
    const id = Number(checkbox.value);
    if (checkbox.checked) state.selectedTeamIds.add(id);
    else state.selectedTeamIds.delete(id);
    updateEntryTeamSelect();
    updateScopeCopy();
    await scopeChanged();
  }

  async function scopeChanged() {
    try {
      await Promise.all([loadDashboard(), loadComparison()]);
    } catch (error) {
      handleApiError(error, "No se pudo cambiar el alcance.");
    }
  }

  function renderTeamManager() {
    const container = $("#team-manager-list");
    if (!state.teams.length) {
      container.innerHTML = '<div class="empty-inline"><span aria-hidden="true">◇</span><p>No hay equipos registrados.</p></div>';
      return;
    }
    container.innerHTML = state.teams.map((team) => `
      <div class="team-manager-row">
        <span><strong>${escapeHtml(team.name)}</strong><small>${team.archived ? "Archivado · sus datos se conservan" : "Activo"}</small></span>
        <button class="button button--ghost" type="button" data-team-archive="${Number(team.id)}" data-archived="${Boolean(team.archived)}">
          ${team.archived ? "Reactivar" : "Archivar"}
        </button>
      </div>
    `).join("");
  }

  async function handleTeamManagerClick(event) {
    const button = event.target.closest("[data-team-archive]");
    if (!button) return;
    const id = Number(button.dataset.teamArchive);
    const currentlyArchived = button.dataset.archived === "true";
    setBusy(button, true, currentlyArchived ? "Reactivando…" : "Archivando…");
    try {
      await api(`/api/teams/${id}`, { method: "PATCH", body: { archived: !currentlyArchived } });
      if (!currentlyArchived) state.selectedTeamIds.delete(id);
      await loadTeams();
      await scopeChanged();
      showToast(currentlyArchived ? "Equipo reactivado" : "Equipo archivado", "Sus registros históricos permanecen intactos.");
    } catch (error) {
      handleApiError(error, "No se pudo actualizar el equipo.");
      setBusy(button, false);
    }
  }

  async function loadDashboard() {
    const ids = [...state.selectedTeamIds];
    const query = ids.length ? `?team_ids=${encodeURIComponent(ids.join(","))}` : "";
    $("#metric-grid").setAttribute("aria-busy", "true");
    const dashboard = await api(`/api/dashboard${query}`);
    state.dashboard = dashboard;
    renderDashboard();
    $("#metric-grid").setAttribute("aria-busy", "false");
  }

  function renderDashboard() {
    const dashboard = state.dashboard || {};
    const totals = dashboard.totals || {};
    setAnimatedCount($("#kpi-observations"), totals.observations);
    setAnimatedCount($("#kpi-adjustments"), totals.adjustments);
    setAnimatedCount($("#kpi-matches"), totals.matches);
    renderMetrics(Array.isArray(dashboard.groups) ? dashboard.groups : []);
    populateComparisonGroups();
  }

  function groupKind(group) {
    const key = `${group.key || ""} ${(group.categories || []).map((item) => item.key).join(" ")}`.toLowerCase();
    if (key.includes("total_shots_range")) return "totalShots";
    if (key.includes("shots_on_target_range")) return "targetRange";
    if (key.includes("corners_range")) return "cornersRange";
    if (key.includes("cards_range")) return "cards";
    if (key.includes("half_goals")) return "halves";
    if (key.includes("home_win") || key.includes("away_win") || key.includes("result")) return "result";
    if (key.includes("over25") || key.includes("under25") || key.includes("goal")) {
      if (key.includes("local_scored") || key.includes("local_blank")) return "local";
      return "goals";
    }
    if (key.includes("btts")) return "btts";
    if (key.includes("local_scored") || key.includes("local_blank")) return "local";
    if (key.includes("corner")) return "corners";
    if (key.includes("shot")) return "shots";
    return "fallback";
  }

  function groupColors(group) {
    return COLOR_SETS[groupKind(group)] || COLOR_SETS.fallback;
  }

  function normalizeCategories(group) {
    const total = Math.max(0, Number(group.total) || 0);
    return (group.categories || []).map((category) => {
      const count = Math.max(0, Number(category.count) || 0);
      const provided = Number(category.percentage);
      const percentage = Number.isFinite(provided) ? provided : (total ? (count / total) * 100 : 0);
      return { ...category, count, percentage: Math.max(0, Math.min(100, percentage)) };
    });
  }

  function decrementableCount(category) {
    const safeCapacity = Number(category?.decrementable_count);
    if (Number.isFinite(safeCapacity)) return Math.max(0, safeCapacity);
    return Math.max(0, Number(category?.manual_count) || 0);
  }

  function renderMetrics(groups) {
    const grid = $("#metric-grid");
    if (!groups.length) {
      grid.innerHTML = '<div class="empty-state"><span aria-hidden="true">◇</span><h3>Sin variables disponibles</h3><p>El aplicativo todavía no ha definido sus marcadores.</p></div>';
      $("#insight-copy").textContent = "Todavía no hay variables para explicar.";
      $("#insight-formula").textContent = "";
      return;
    }

    grid.innerHTML = groups.map((group, index) => metricCardHtml(group, index)).join("");
    const firstGroup = groups[0];
    const selectedGroup = groups.find((group) => String(group.key) === String(state.activeMetricGroupKey)) || firstGroup;
    const categories = normalizeCategories(selectedGroup);
    const selectedKey = state.selectedCategories.get(selectedGroup.key) || categories[0]?.key;
    if (selectedKey) selectMetricCategory(selectedGroup.key, selectedKey, false);
  }

  function metricCardHtml(group, cardIndex = 0) {
    const categories = normalizeCategories(group);
    const colors = groupColors(group);
    const total = Math.max(0, Number(group.total) || categories.reduce((sum, item) => sum + item.count, 0));
    let selectedKey = state.selectedCategories.get(group.key);
    if (!categories.some((category) => category.key === selectedKey)) selectedKey = categories[0]?.key;
    if (selectedKey) state.selectedCategories.set(group.key, selectedKey);
    const selected = categories.find((category) => category.key === selectedKey) || categories[0];
    let offset = 0;
    const circles = total ? categories.map((category, index) => {
      const percentage = category.percentage;
      const circle = `<circle class="donut__segment${category.key === selectedKey ? " is-selected" : ""}" data-chart-category="${escapeHtml(category.key)}" pathLength="100" cx="60" cy="60" r="45" stroke="${colors[index % colors.length]}" stroke-dasharray="${percentage} ${100 - percentage}" stroke-dashoffset="${-offset}" style="--segment-offset:${-offset};--segment-delay:${index * 90}ms"><title>${escapeHtml(category.label)}: ${formatPercent(percentage)}</title></circle>`;
      offset += percentage;
      return circle;
    }).join("") : "";

    const options = categories.map((category, index) => `
      <div class="metric-option${category.key === selectedKey ? " is-selected" : ""}" data-option-key="${escapeHtml(category.key)}">
        <button class="metric-option__label" type="button" data-select-category="${escapeHtml(category.key)}">
          <span class="metric-option__dot" style="background:${colors[index % colors.length]}" aria-hidden="true"></span>
          <span class="metric-option__text"><strong>${escapeHtml(category.label)}</strong><small>${formatPercent(category.percentage)} · ${formatCount(category.manual_count)} manual${Number(category.match_count) ? ` + ${formatCount(category.match_count)} partido${Number(category.match_count) === 1 ? "" : "s"}` : ""}</small></span>
        </button>
        <div class="stepper" aria-label="Contador de ${escapeHtml(category.label)}">
          <button type="button" data-adjust="-1" data-variable="${escapeHtml(category.key)}" aria-label="Restar uno a ${escapeHtml(category.label)}" ${category.can_decrement === false || decrementableCount(category) <= 0 ? "disabled" : ""}>−</button>
          <output aria-label="${formatCount(category.count)} registros">${formatCount(category.count)}</output>
          <button type="button" data-adjust="1" data-variable="${escapeHtml(category.key)}" aria-label="Sumar uno a ${escapeHtml(category.label)}">＋</button>
        </div>
      </div>
    `).join("");

    return `
      <article class="metric-card" data-group-key="${escapeHtml(group.key)}" style="--card-index:${cardIndex}">
        <header class="metric-card__header">
          <div><h3>${escapeHtml(group.label)}</h3><p>${formatCount(total)} observaciones en esta variable</p></div>
          <button class="metric-info" type="button" data-metric-info aria-label="Explicar ${escapeHtml(group.label)}">i</button>
        </header>
        <div class="donut-wrap">
          <svg class="donut" viewBox="0 0 120 120" role="img" aria-label="${escapeHtml(group.label)}: ${categories.map((item) => `${item.label} ${formatPercent(item.percentage)}`).join(", ")}">
            <circle class="donut__base" cx="60" cy="60" r="45"></circle>${circles}
          </svg>
          <div class="donut__center"><strong>${total ? formatPercent(selected?.percentage) : "Sin datos"}</strong><span>${total ? escapeHtml(selected?.label) : "Agrega registros"}</span></div>
        </div>
        <div class="metric-options">${options}</div>
        <form class="metric-batch" data-batch-form>
          <div class="metric-batch__top">
            <label class="sr-only" for="batch-option-${escapeHtml(group.key)}">Opción del lote</label>
            <select id="batch-option-${escapeHtml(group.key)}" name="variable" aria-label="Opción del lote">${categories.map((category) => `<option value="${escapeHtml(category.key)}" data-decrementable-count="${decrementableCount(category)}">${escapeHtml(category.label)}</option>`).join("")}</select>
            <label class="sr-only" for="batch-value-${escapeHtml(group.key)}">Cantidad</label>
            <input id="batch-value-${escapeHtml(group.key)}" name="quantity" type="number" min="1" max="10000" value="10" inputmode="numeric" aria-label="Cantidad del lote">
          </div>
          <label class="sr-only" for="batch-note-${escapeHtml(group.key)}">Nota del lote</label>
          <input id="batch-note-${escapeHtml(group.key)}" name="note" type="text" maxlength="500" placeholder="Nota opcional del lote">
          <div class="metric-batch__actions">
            <button class="button button--ghost" type="button" data-batch-direction="-1" ${decrementableCount(categories[0]) > 0 ? "" : "disabled"}>− Restar corrección</button>
            <button class="button button--secondary" type="button" data-batch-direction="1">＋ Sumar lote</button>
          </div>
        </form>
      </article>
    `;
  }

  function findDashboardGroup(groupKey) {
    return state.dashboard?.groups?.find((group) => String(group.key) === String(groupKey));
  }

  function selectMetricCategory(groupKey, categoryKey, scroll = false) {
    const group = findDashboardGroup(groupKey);
    if (!group) return;
    const categories = normalizeCategories(group);
    const category = categories.find((item) => String(item.key) === String(categoryKey));
    if (!category) return;
    state.activeMetricGroupKey = groupKey;
    state.selectedCategories.set(groupKey, categoryKey);
    $$(".metric-card").forEach((card) => card.classList.toggle("is-selected", card.dataset.groupKey === String(groupKey)));
    const card = $(`.metric-card[data-group-key="${CSS.escape(String(groupKey))}"]`);
    if (card) {
      $$(".metric-option", card).forEach((row) => row.classList.toggle("is-selected", row.dataset.optionKey === String(categoryKey)));
      $$(".donut__segment", card).forEach((segment) => segment.classList.toggle("is-selected", segment.dataset.chartCategory === String(categoryKey)));
      const center = $(".donut__center", card);
      const total = Number(group.total) || 0;
      center.innerHTML = `<strong>${total ? formatPercent(category.percentage) : "Sin datos"}</strong><span>${total ? escapeHtml(category.label) : "Agrega registros"}</span>`;
    }
    renderInsight(group, category);
    if (scroll) $("#insight-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderInsight(group, category) {
    const categories = normalizeCategories(group);
    const total = Number(group.total) || categories.reduce((sum, item) => sum + item.count, 0);
    $("#insight-title").textContent = group.label || "Lectura de la variable";
    if (!total) {
      $("#insight-copy").textContent = `${GROUP_HELP[groupKind(group)] || "Esta tarjeta compara sus opciones."} Todavía no hay observaciones para calcular porcentajes.`;
      $("#insight-formula").textContent = "Agrega el primer dato para iniciar el cálculo.";
      return;
    }

    const rivals = categories.filter((item) => item.key !== category.key);
    const closest = [...rivals].sort((a, b) => b.percentage - a.percentage)[0];
    let comparison = "";
    if (closest) {
      const difference = Math.abs(category.percentage - closest.percentage);
      if (Math.abs(difference) < 0.05) comparison = ` Está igualado con ${closest.label}.`;
      else comparison = ` ${category.percentage > closest.percentage ? "Supera" : "Está por debajo de"} ${closest.label} por ${formatPercent(difference).replace(" %", "")} puntos porcentuales.`;
    }
    $("#insight-copy").textContent = `De ${formatCount(total)} observaciones, ${formatCount(category.count)} fueron ${category.label} (${formatPercent(category.percentage)}).${comparison} ${GROUP_HELP[groupKind(group)] || ""}`;
    $("#insight-formula").textContent = `${formatCount(category.count)} ÷ ${formatCount(total)} × 100 = ${formatPercent(category.percentage)}`;
  }

  async function handleMetricClick(event) {
    const card = event.target.closest(".metric-card");
    if (!card) return;
    const groupKey = card.dataset.groupKey;
    const selectButton = event.target.closest("[data-select-category]");
    const segment = event.target.closest("[data-chart-category]");
    const infoButton = event.target.closest("[data-metric-info]");
    const adjustButton = event.target.closest("[data-adjust]");
    const batchButton = event.target.closest("[data-batch-direction]");

    if (selectButton || segment) {
      selectMetricCategory(groupKey, (selectButton || segment).dataset.selectCategory || segment?.dataset.chartCategory);
      return;
    }
    if (infoButton) {
      const group = findDashboardGroup(groupKey);
      const selectedKey = state.selectedCategories.get(groupKey) || group?.categories?.[0]?.key;
      selectMetricCategory(groupKey, selectedKey, true);
      return;
    }
    if (adjustButton) {
      const delta = Number(adjustButton.dataset.adjust);
      await applyAdjustment(adjustButton.dataset.variable, delta, "", adjustButton);
      return;
    }
    if (batchButton) {
      const form = batchButton.closest("[data-batch-form]");
      const values = Object.fromEntries(new FormData(form));
      const quantity = Number(values.quantity);
      const direction = Number(batchButton.dataset.batchDirection);
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > 10000) {
        showToast("Cantidad inválida", "Usa un número entre 1 y 10.000.", { error: true });
        return;
      }
      if (direction < 0) {
        const available = targetDecrementableCount(values.variable);
        if (quantity > available) {
          showToast("Corrección demasiado alta", `La capacidad segura de resta es ${formatCount(available)}. Los partidos detallados son inmutables.`, { error: true });
          return;
        }
        const confirmed = await confirmAction(
          "Registrar corrección",
          `Se restarán ${formatCount(quantity)} observaciones. El historial conservará tanto el registro original como esta corrección.`,
          "Restar corrección"
        );
        if (!confirmed) return;
      }
      await applyAdjustment(values.variable, quantity * direction, values.note?.trim() || "", batchButton);
      if (direction > 0) form.reset();
    }
  }

  function handleMetricChange(event) {
    const select = event.target.closest('[data-batch-form] select[name="variable"]');
    if (!select) return;
    const form = select.closest("[data-batch-form]");
    const subtractButton = $('[data-batch-direction="-1"]', form);
    const available = Number(select.selectedOptions[0]?.dataset.decrementableCount) || 0;
    subtractButton.disabled = available <= 0;
  }

  async function applyAdjustment(variable, delta, note = "", sourceButton = null, allowUndo = true, targetTeamId = undefined) {
    if (!variable || !Number.isInteger(Number(delta)) || Number(delta) === 0) return;
    const teamId = targetTeamId !== undefined
      ? targetTeamId
      : (state.entryTeamId ? Number(state.entryTeamId) : null);
    setBusy(sourceButton, true, "…");
    requestStarted();
    try {
      await api("/api/adjustments", {
        method: "POST",
        body: { variable, delta: Number(delta), team_id: teamId, note },
      });
      await Promise.all([loadDashboard(), loadComparison()]);
      requestFinished(true);
      const variableLabel = state.variables.find((item) => item.key === variable)?.label || variable;
      const destination = teamId ? state.teams.find((team) => Number(team.id) === teamId)?.name : "Global";
      showToast(
        delta > 0 ? "Datos sumados" : "Corrección registrada",
        `${delta > 0 ? "+" : ""}${formatCount(delta)} en ${variableLabel} · ${destination || "Global"}`,
        allowUndo ? {
          actionLabel: "Deshacer",
          onAction: () => applyAdjustment(variable, -Number(delta), `Reversión del movimiento anterior${note ? `: ${note}` : ""}`, null, false, teamId),
          duration: 8000,
        } : {}
      );
    } catch (error) {
      requestFinished(false);
      handleApiError(error, "No se pudo registrar el movimiento.");
    } finally {
      setBusy(sourceButton, false);
    }
  }

  function populateComparisonGroups() {
    const select = $("#comparison-group");
    const groups = state.dashboard?.groups || [];
    const previous = select.value;
    select.innerHTML = groups.map((group) => `<option value="${escapeHtml(group.key)}">${escapeHtml(group.label)}</option>`).join("");
    if (groups.some((group) => String(group.key) === previous)) select.value = previous;
    renderComparison();
  }

  async function loadComparison() {
    const teams = getSelectedTeams();
    state.comparisonDashboards.clear();
    if (teams.length < 2) {
      renderComparison();
      return;
    }
    const results = await Promise.all(teams.map(async (team) => {
      const dashboard = await api(`/api/dashboard?team_ids=${encodeURIComponent(team.id)}`);
      return [Number(team.id), dashboard];
    }));
    state.comparisonDashboards = new Map(results);
    renderComparison();
    refreshAdjustmentAvailability();
  }

  function targetCategory(variable) {
    let dashboard = state.dashboard;
    if (state.selectedTeamIds.size > 1 && state.entryTeamId) {
      dashboard = state.comparisonDashboards.get(Number(state.entryTeamId)) || null;
    }
    for (const group of dashboard?.groups || []) {
      const category = (group.categories || []).find((item) => item.key === variable);
      if (category) return category;
    }
    return null;
  }

  function targetDecrementableCount(variable) {
    return decrementableCount(targetCategory(variable));
  }

  function refreshAdjustmentAvailability() {
    $$('#metric-grid [data-adjust="-1"]').forEach((button) => {
      button.disabled = targetDecrementableCount(button.dataset.variable) <= 0;
    });
    $$('#metric-grid [data-batch-form]').forEach((form) => {
      const select = $('select[name="variable"]', form);
      if (!select) return;
      [...select.options].forEach((option) => {
        option.dataset.decrementableCount = String(targetDecrementableCount(option.value));
      });
      const subtractButton = $('[data-batch-direction="-1"]', form);
      subtractButton.disabled = targetDecrementableCount(select.value) <= 0;
    });
  }

  function renderComparison() {
    const container = $("#comparison-content");
    const teams = getSelectedTeams();
    if (teams.length < 2) {
      $("#comparison-subtitle").textContent = "Selecciona al menos dos equipos para contrastar sus porcentajes.";
      container.innerHTML = '<div class="empty-inline"><span aria-hidden="true">◇</span><p>Elige dos o más equipos arriba.</p></div>';
      return;
    }
    if (state.comparisonDashboards.size < teams.length) {
      container.innerHTML = '<div class="empty-inline"><span aria-hidden="true">↻</span><p>Preparando comparación…</p></div>';
      return;
    }

    const groupKey = $("#comparison-group").value || state.dashboard?.groups?.[0]?.key;
    const referenceGroup = state.dashboard?.groups?.find((group) => String(group.key) === String(groupKey));
    if (!referenceGroup) return;
    const colors = groupColors(referenceGroup);
    $("#comparison-subtitle").textContent = `${teams.length} equipos · ${referenceGroup.label}`;
    container.innerHTML = teams.map((team) => {
      const dashboard = state.comparisonDashboards.get(Number(team.id));
      const group = dashboard?.groups?.find((item) => String(item.key) === String(groupKey));
      const categories = group ? normalizeCategories(group) : [];
      const segments = categories.map((category, index) => `<span class="comparison-row__segment" style="width:${category.percentage}%;background:${colors[index % colors.length]}" title="${escapeHtml(category.label)}: ${formatPercent(category.percentage)}"></span>`).join("");
      const values = categories.map((category) => `${category.label} ${formatPercent(category.percentage)}`).join(" · ") || "Sin datos";
      return `<div class="comparison-row"><span class="comparison-row__team">${escapeHtml(team.name)}</span><span class="comparison-row__track" role="img" aria-label="${escapeHtml(values)}">${segments}</span><span class="comparison-row__value">${escapeHtml(values)}</span></div>`;
    }).join("");
  }

  function populateVariableFilters() {
    const select = $("#history-variable");
    select.innerHTML = '<option value="all">Todas</option>' + state.variables.map((variable) => `<option value="${escapeHtml(variable.key)}">${escapeHtml(variable.label)}</option>`).join("");
  }

  async function loadHistory() {
    const type = new FormData($("#history-filters")).get("type") || "all";
    const params = new URLSearchParams({ page: String(state.historyPage), page_size: "25" });
    if (type !== "all") params.set("type", type);
    try {
      const data = await api(`/api/history?${params}`);
      state.history = {
        items: Array.isArray(data?.items) ? data.items : [],
        page: Number(data?.page) || state.historyPage,
        page_size: Number(data?.page_size) || 25,
        total: Number(data?.total) || 0,
        total_pages: Math.max(1, Number(data?.total_pages) || 1),
      };
      state.historyPage = state.history.page;
      renderHistory();
    } catch (error) {
      handleApiError(error, "No se pudo cargar el historial.");
    }
  }

  function renderHistory() {
    const values = Object.fromEntries(new FormData($("#history-filters")));
    const query = String(values.search || "").trim().toLocaleLowerCase("es");
    const variable = values.variable || "all";
    const items = state.history.items.filter((item) => {
      if (variable !== "all" && item.type === "adjustment" && item.variable !== variable) return false;
      if (variable !== "all" && item.type === "match" && !(item.categories || []).includes(variable)) return false;
      if (!query) return true;
      return JSON.stringify(item).toLocaleLowerCase("es").includes(query);
    });

    const tbody = $("#history-body");
    tbody.innerHTML = items.map(historyRowHtml).join("");
    $("#history-empty").hidden = items.length > 0;
    $("#history-page").textContent = `Página ${state.history.page} de ${state.history.total_pages} · ${formatCount(state.history.total)} movimientos`;
    $("#history-prev").disabled = state.history.page <= 1;
    $("#history-next").disabled = state.history.page >= state.history.total_pages;
  }

  function historyRowHtml(item) {
    if (item.type === "match") {
      const home = item.home_team_name || item.home_team || "Local";
      const away = item.away_team_name || item.away_team || "Visitante";
      const homeGoals = Number(item.home_goals);
      const awayGoals = Number(item.away_goals);
      const hasScore = item.home_goals !== null && item.home_goals !== undefined && item.home_goals !== ""
        && item.away_goals !== null && item.away_goals !== undefined && item.away_goals !== ""
        && Number.isInteger(homeGoals) && Number.isInteger(awayGoals);
      const score = hasScore ? `${homeGoals}–${awayGoals}` : "Marcador no disponible";
      const extras = [];
      if (item.corners_home != null && item.corners_away != null) extras.push(`Córners ${item.corners_home}–${item.corners_away}`);
      if (item.shots_on_target_home != null && item.shots_on_target_away != null) extras.push(`Tiros ${item.shots_on_target_home}–${item.shots_on_target_away}`);
      return `<tr>
        <td>${safeDate(item.created_at)}</td>
        <td><span class="event-badge event-badge--match">Partido</span></td>
        <td><strong>${escapeHtml(home)} ${escapeHtml(score)} ${escapeHtml(away)}</strong>${extras.length ? `<br><small>${escapeHtml(extras.join(" · "))}</small>` : ""}</td>
        <td>${escapeHtml(home)} / ${escapeHtml(away)}</td>
        <td><span class="delta-positive">Variables calculadas</span></td>
        <td>${escapeHtml(item.note || "—")}</td>
      </tr>`;
    }
    const delta = Number(item.delta) || 0;
    return `<tr>
      <td>${safeDate(item.created_at)}</td>
      <td><span class="event-badge">Ajuste</span></td>
      <td><strong>${escapeHtml(item.variable_label || item.variable || "Variable")}</strong></td>
      <td>${escapeHtml(item.team_name || "Global")}</td>
      <td><span class="${delta >= 0 ? "delta-positive" : "delta-negative"}">${delta > 0 ? "+" : ""}${formatCount(delta)}</span></td>
      <td>${escapeHtml(item.note || "—")}</td>
    </tr>`;
  }

  function populateMatchTeamOptions() {
    const activeTeams = state.teams.filter((team) => !team.archived);
    [$("#match-form select[name='home_team_id']"), $("#match-form select[name='away_team_id']")].forEach((select) => {
      if (!select) return;
      const previous = select.value;
      select.innerHTML = '<option value="">Sin especificar</option>' + activeTeams.map((team) => `<option value="${Number(team.id)}">${escapeHtml(team.name)}</option>`).join("");
      if ([...select.options].some((option) => option.value === previous)) select.value = previous;
    });
  }

  function openMatchDialog() {
    if (state.features.matches === false) {
      showToast("Función no disponible", "Esta instalación no admite partidos detallados.", { error: true });
      return;
    }
    populateMatchTeamOptions();
    showFormError($("#match-error"), "");
    $("#match-dialog").showModal();
  }

  async function handleMatchSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const raw = Object.fromEntries(new FormData(form));
    const optionalNumbers = ["home_team_id", "away_team_id", "corners_home", "corners_away", "shots_on_target_home", "shots_on_target_away"];
    const homeGoalsRaw = String(raw.home_goals ?? "").trim();
    const awayGoalsRaw = String(raw.away_goals ?? "").trim();
    if (!homeGoalsRaw || !awayGoalsRaw) {
      showFormError($("#match-error"), "Ingresa los goles del equipo local y del visitante.");
      return;
    }
    const body = { ...raw, home_goals: Number(homeGoalsRaw), away_goals: Number(awayGoalsRaw) };
    optionalNumbers.forEach((key) => { body[key] = raw[key] === "" ? null : Number(raw[key]); });
    if (!Number.isInteger(body.home_goals) || body.home_goals < 0 || body.home_goals > 100
      || !Number.isInteger(body.away_goals) || body.away_goals < 0 || body.away_goals > 100) {
      showFormError($("#match-error"), "Ingresa un marcador válido para ambos equipos.");
      return;
    }
    if (body.home_team_id && body.away_team_id && body.home_team_id === body.away_team_id) {
      showFormError($("#match-error"), "El equipo local y el visitante deben ser diferentes.");
      return;
    }
    setBusy(button, true, "Guardando…");
    requestStarted();
    try {
      await api("/api/matches", { method: "POST", body });
      form.reset();
      $("#match-dialog").close();
      await Promise.all([loadDashboard(), loadComparison()]);
      requestFinished(true);
      showToast("Partido registrado", "Sus variables ya se sumaron a los porcentajes.");
    } catch (error) {
      requestFinished(false);
      showFormError($("#match-error"), error.message);
    } finally {
      setBusy(button, false);
    }
  }

  async function downloadExport(format, sourceButton) {
    if (PREVIEW_MODE) {
      showToast("Descarga desactivada", "Abre el aplicativo para exportar tus datos reales.");
      return;
    }
    setBusy(sourceButton, true, "Preparando…");
    try {
      const response = await fetch(`/api/export?format=${encodeURIComponent(format)}`, {
        credentials: "same-origin",
        headers: { Accept: "application/octet-stream,application/json,text/csv" },
      });
      if (!response.ok) {
        let message = "No se pudo preparar la descarga.";
        try {
          const payload = await response.json();
          message = payload?.error?.message || message;
        } catch (error) { /* The error body may not be JSON. */ }
        throw new ApiError(message, response.status);
      }
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const match = disposition.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i);
      const filename = match ? decodeURIComponent(match[1].replaceAll('"', "")) : `betplaycito-respaldo.${format}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      showToast("Descarga lista", filename);
    } catch (error) {
      handleApiError(error, "No se pudo exportar el archivo.");
    } finally {
      setBusy(sourceButton, false);
    }
  }

  async function createServerBackup(event) {
    const button = event.currentTarget;
    setBusy(button, true, "Creando…");
    try {
      const data = await api("/api/backup", { method: "POST" });
      showToast("Copia creada", data?.filename || data?.path || "El respaldo quedó guardado en el equipo.");
    } catch (error) {
      handleApiError(error, "No se pudo crear la copia.");
    } finally {
      setBusy(button, false);
    }
  }

  async function handleRestoreFile(event) {
    if (PREVIEW_MODE) {
      event.target.value = "";
      showToast("Restauración desactivada", "Esta vista previa no lee ni modifica respaldos.");
      return;
    }
    const file = event.target.files?.[0];
    state.restorePayload = null;
    $("#restore-button").disabled = true;
    $("#restore-file-name").textContent = file?.name || "Ningún archivo seleccionado";
    if (!file) return;
    if (file.size > 50 * 1024 * 1024) {
      showToast("Archivo demasiado grande", "El respaldo supera los 50 MB permitidos.", { error: true });
      event.target.value = "";
      return;
    }
    try {
      const parsed = JSON.parse(await file.text());
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new TypeError("El respaldo debe ser un objeto JSON.");
      }
      state.restorePayload = parsed;
      $("#restore-button").disabled = false;
      $("#restore-file-name").textContent = `${file.name} · JSON leído, pendiente de validar`;
      showToast("JSON leído", "Está pendiente de validación por el aplicativo.");
    } catch (error) {
      $("#restore-file-name").textContent = `${file.name} · JSON no válido`;
      showToast("JSON inválido", "Selecciona un respaldo generado por este aplicativo.", { error: true });
    }
  }

  async function restoreBackup(event) {
    if (!state.restorePayload) return;
    const confirmed = await confirmAction(
      "Restaurar respaldo",
      "Esta operación REEMPLAZA los equipos, ajustes y partidos actuales por los del archivo. Antes del reemplazo, el aplicativo crea automáticamente una copia de seguridad recuperable.",
      "Reemplazar con respaldo"
    );
    if (!confirmed) return;
    const button = event.currentTarget;
    setBusy(button, true, "Restaurando…");
    requestStarted();
    try {
      await api("/api/restore", { method: "POST", body: state.restorePayload });
      state.restorePayload = null;
      $("#restore-file").value = "";
      $("#restore-file-name").textContent = "Ningún archivo seleccionado";
      await loadTeams();
      await loadDashboard();
      requestFinished(true);
      showToast("Respaldo restaurado", "Los datos del panel ya fueron actualizados.");
      setView("dashboard");
    } catch (error) {
      requestFinished(false);
      handleApiError(error, "No se pudo restaurar el respaldo.");
    } finally {
      setBusy(button, false);
      button.disabled = !state.restorePayload;
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const errorElement = $("#password-error");
    showFormError(errorElement, "");
    if (values.new_password !== values.confirmation) {
      showFormError(errorElement, "La confirmación no coincide con la nueva contraseña.");
      return;
    }
    const button = $('button[type="submit"]', form);
    setBusy(button, true, "Actualizando…");
    try {
      await api("/api/password", {
        method: "POST",
        body: { current_password: values.current_password, new_password: values.new_password },
      });
      form.reset();
      showToast("Contraseña actualizada", "La nueva contraseña ya está activa.");
    } catch (error) {
      showFormError(errorElement, error.message);
    } finally {
      setBusy(button, false);
    }
  }

  async function shutdownApp() {
    const confirmed = await confirmAction(
      "Cerrar aplicación",
      "Se cerrará el proceso local después de guardar las operaciones pendientes. Podrás abrirlo de nuevo desde el ejecutable.",
      "Cerrar aplicación"
    );
    if (!confirmed) return;
    try {
      await api("/api/shutdown", { method: "POST" });
      document.body.innerHTML = '<main class="auth-panel"><div class="auth-card"><p class="eyebrow">Aplicación cerrada</p><h1>Todo quedó guardado.</h1><p style="color:var(--text-soft)">Ya puedes cerrar esta ventana. Para volver a entrar, abre nuevamente BetPlaycito Nelson.</p></div></main>';
      window.setTimeout(() => window.close(), 500);
    } catch (error) {
      handleApiError(error, "No se pudo cerrar la aplicación.");
    }
  }

  function confirmAction(title, message, actionLabel = "Confirmar") {
    const dialog = $("#confirm-dialog");
    $("#confirm-title").textContent = title;
    $("#confirm-message").textContent = message;
    $("#confirm-action").textContent = actionLabel;
    dialog.returnValue = "cancel";
    dialog.showModal();
    return new Promise((resolve) => {
      dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
    });
  }

  function handleApiError(error, fallback) {
    if (error?.status === 401) {
      showAuth("login", "Tu sesión terminó. Ingresa de nuevo.");
      return;
    }
    showToast("No se completó la acción", error?.message || fallback, { error: true, duration: 7000 });
  }

  function openSidebar() {
    $("#sidebar").classList.add("is-open");
    $("#sidebar-scrim").hidden = false;
    $("#menu-button").setAttribute("aria-expanded", "true");
  }

  function closeSidebar() {
    $("#sidebar").classList.remove("is-open");
    $("#sidebar-scrim").hidden = true;
    $("#menu-button").setAttribute("aria-expanded", "false");
  }

  function bindEvents() {
    $("#login-form").addEventListener("submit", handleLogin);
    $("#setup-form").addEventListener("submit", handleSetup);
    $$(".password-toggle").forEach((button) => button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.passwordTarget);
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.setAttribute("aria-label", showing ? "Mostrar contraseña" : "Ocultar contraseña");
    }));

    $$('[data-view]').forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
    $("#logout-button").addEventListener("click", handleLogout);
    $("#shutdown-button").addEventListener("click", shutdownApp);
    $("#menu-button").addEventListener("click", () => $("#sidebar").classList.contains("is-open") ? closeSidebar() : openSidebar());
    $("#sidebar-scrim").addEventListener("click", closeSidebar);

    $("#add-team-form").addEventListener("submit", handleCreateTeam);
    $("#team-chips").addEventListener("change", handleTeamSelection);
    $("#entry-team-select").addEventListener("change", (event) => {
      state.entryTeamId = event.target.value;
      refreshAdjustmentAvailability();
    });
    $("#manage-teams-button").addEventListener("click", () => $("#teams-dialog").showModal());
    $("#team-manager-list").addEventListener("click", handleTeamManagerClick);
    $("#comparison-group").addEventListener("change", renderComparison);
    $("#metric-grid").addEventListener("click", handleMetricClick);
    $("#metric-grid").addEventListener("change", handleMetricChange);

    [$("#open-match-button"), $("#hero-match-button"), $("#mobile-match-button")].forEach((button) => button.addEventListener("click", openMatchDialog));
    $("#match-form").addEventListener("submit", handleMatchSubmit);
    $$('[data-close-dialog]').forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.closeDialog)?.close()));

    $("#history-refresh").addEventListener("click", loadHistory);
    $("#history-filters").addEventListener("change", (event) => {
      if (event.target.name === "type") {
        state.historyPage = 1;
        loadHistory();
      } else renderHistory();
    });
    let searchTimer;
    $("#history-filters input[name='search']").addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(renderHistory, 160);
    });
    $("#history-prev").addEventListener("click", () => { if (state.historyPage > 1) { state.historyPage -= 1; loadHistory(); } });
    $("#history-next").addEventListener("click", () => { if (state.historyPage < state.history.total_pages) { state.historyPage += 1; loadHistory(); } });

    $$('[data-export]').forEach((button) => button.addEventListener("click", () => downloadExport(button.dataset.export, button)));
    $("#create-backup-button").addEventListener("click", createServerBackup);
    $("#restore-file").addEventListener("change", handleRestoreFile);
    $("#restore-button").addEventListener("click", restoreBackup);
    $("#password-form").addEventListener("submit", changePassword);

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && $("#sidebar").classList.contains("is-open")) closeSidebar();
    });
  }

  boot();
})();
