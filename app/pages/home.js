import { createDocumentPreview } from "../components/DocumentPreview.js";
import { createTemplateGallery } from "../components/TemplateGallery.js";
import { lekhxApi } from "../lib/api.js";

const FORMAT_OPTIONS = [
  { id: "doc", label: "Word" },
  { id: "pdf", label: "PDF" },
  { id: "excel", label: "Excel" },
  { id: "powerpoint", label: "PPT" },
  { id: "notes", label: "Notes" },
];

export function renderHome() {
  const main = document.createElement("main");
  main.className = "lekhx-workspace";

  const state = {
    format: "doc",
    language: "en",
    templateId: "",
    title: "",
    prompt: "",
    busy: false,
    error: null,
    languages: [],
    templates: [],
    history: [],
    activeDoc: null,
    health: null,
  };

  const sidebar = document.createElement("aside");
  sidebar.className = "lekhx-stack";

  const form = document.createElement("form");
  form.className = "lekhx-card lekhx-stack";

  const formatField = document.createElement("div");
  const formatLabel = document.createElement("span");
  formatLabel.className = "lekhx-label";
  formatLabel.textContent = "Office Format";
  const formatGrid = document.createElement("div");
  formatGrid.className = "lekhx-format-grid";
  formatField.append(formatLabel, formatGrid);

  const langField = document.createElement("div");
  const langLabel = document.createElement("label");
  langLabel.className = "lekhx-label";
  langLabel.htmlFor = "lekhx-lang";
  langLabel.textContent = "Language";
  const langSelect = document.createElement("select");
  langSelect.id = "lekhx-lang";
  langSelect.className = "lekhx-select";
  langSelect.addEventListener("change", function () {
    state.language = langSelect.value;
  });
  langField.append(langLabel, langSelect);

  const templateSlot = document.createElement("div");

  const titleField = document.createElement("div");
  const titleLabel = document.createElement("label");
  titleLabel.className = "lekhx-label";
  titleLabel.htmlFor = "lekhx-title";
  titleLabel.textContent = "Document Title (Optional)";
  const titleInput = document.createElement("input");
  titleInput.id = "lekhx-title";
  titleInput.className = "lekhx-input";
  titleInput.placeholder = "Quarterly Operations Summary";
  titleInput.addEventListener("input", function () {
    state.title = titleInput.value;
  });
  titleField.append(titleLabel, titleInput);

  const promptField = document.createElement("div");
  const promptLabel = document.createElement("label");
  promptLabel.className = "lekhx-label";
  promptLabel.htmlFor = "lekhx-prompt";
  promptLabel.textContent = "Content & Instructions";
  const promptInput = document.createElement("textarea");
  promptInput.id = "lekhx-prompt";
  promptInput.className = "lekhx-textarea";
  promptInput.required = true;
  promptInput.placeholder =
    "Paste points, table rows (col1 | col2 | col3), or notes to structure into an office file...";
  promptInput.addEventListener("input", function () {
    state.prompt = promptInput.value;
  });
  promptField.append(promptLabel, promptInput);

  const errorBox = document.createElement("div");
  errorBox.className = "lekhx-error";
  errorBox.hidden = true;

  const submitBtn = document.createElement("button");
  submitBtn.className = "lekhx-primary-btn";
  submitBtn.type = "submit";

  form.append(
    formatField,
    langField,
    templateSlot,
    titleField,
    promptField,
    errorBox,
    submitBtn
  );

  const historyCard = document.createElement("div");
  historyCard.className = "lekhx-card";

  sidebar.append(form, historyCard);

  const previewSection = document.createElement("section");
  main.append(sidebar, previewSection);

  function updateHeaderBadges() {
    const container = document.getElementById("lekhx-status-badges");
    if (!container || !state.health) {
      return;
    }
    container.replaceChildren();
    const pills = [
      `HF Dataset: ${state.health.huggingface_repo || "drishtijs/LekhX"}`,
      `Runtime: ${
        state.health.llm_runtime && state.health.llm_runtime.available
          ? "llama.cpp online"
          : "Deterministic offline"
      }`,
    ];
    if (state.health.hardware && state.health.hardware.tier) {
      pills.push(`Tier: ${state.health.hardware.tier}`);
    }
    for (const text of pills) {
      const span = document.createElement("span");
      span.className = "lekhx-pill";
      span.textContent = text;
      container.appendChild(span);
    }
  }

  function renderFormatButtons() {
    formatGrid.replaceChildren();
    for (const opt of FORMAT_OPTIONS) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `lekhx-format-btn${state.format === opt.id ? " active" : ""}`;
      btn.textContent = opt.label;
      btn.addEventListener("click", function () {
        if (state.format !== opt.id) {
          state.format = opt.id;
          renderFormatButtons();
          renderSubmitState();
          void refreshTemplates();
        }
      });
      formatGrid.appendChild(btn);
    }
  }

  function renderLanguages() {
    langSelect.replaceChildren();
    for (const lang of state.languages) {
      const option = document.createElement("option");
      option.value = lang.code;
      option.textContent = `${lang.native_name} (${lang.name})`;
      if (lang.code === state.language) {
        option.selected = true;
      }
      langSelect.appendChild(option);
    }
  }

  function renderTemplates() {
    templateSlot.replaceChildren(
      createTemplateGallery({
        templates: state.templates,
        selectedTemplateId: state.templateId,
        onSelect(nextId) {
          state.templateId = nextId;
          renderTemplates();
        },
      })
    );
  }

  function renderHistory() {
    historyCard.replaceChildren();
    const label = document.createElement("span");
    label.className = "lekhx-label";
    label.textContent = `Recent Exports (${state.history.length})`;
    historyCard.appendChild(label);

    const list = document.createElement("div");
    list.className = "lekhx-template-list";
    for (const item of state.history) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "lekhx-template-item";
      btn.addEventListener("click", function () {
        state.activeDoc = item;
        renderPreview();
      });

      const nameEl = document.createElement("div");
      nameEl.className = "lekhx-template-title";
      nameEl.textContent = item.title;

      const metaEl = document.createElement("div");
      metaEl.className = "lekhx-template-desc";
      metaEl.textContent = `${String(item.format || "").toUpperCase()} • ${item.language} • ${item.filename}`;

      btn.append(nameEl, metaEl);
      list.appendChild(btn);
    }
    historyCard.appendChild(list);
  }

  function renderPreview() {
    previewSection.replaceChildren(createDocumentPreview(state.activeDoc));
  }

  function renderError() {
    if (state.error) {
      errorBox.hidden = false;
      errorBox.textContent = state.error;
    } else {
      errorBox.hidden = true;
      errorBox.textContent = "";
    }
  }

  function renderSubmitState() {
    submitBtn.disabled = state.busy;
    submitBtn.textContent = state.busy
      ? "Generating Office File..."
      : `Generate ${state.format.toUpperCase()}`;
  }

  async function refreshTemplates() {
    try {
      const res = await lekhxApi.templates(state.format);
      state.templates = res.templates || [];
      if (state.templates.length > 0) {
        state.templateId = state.templates[0].id;
      }
      renderTemplates();
    } catch (_error) {
      // ignore transient load failures when backend is not started yet
    }
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    state.error = null;
    state.busy = true;
    renderError();
    renderSubmitState();
    try {
      const created = await lekhxApi.generate({
        prompt: state.prompt,
        title: state.title.trim() || undefined,
        format: state.format,
        language: state.language,
        template_id: state.templateId || undefined,
      });
      state.activeDoc = created;
      renderPreview();
      const updated = await lekhxApi.documents();
      state.history = updated.documents || [];
      renderHistory();
    } catch (err) {
      state.error = err instanceof Error ? err.message : "Generation failed.";
      renderError();
    } finally {
      state.busy = false;
      renderSubmitState();
    }
  });

  renderFormatButtons();
  renderTemplates();
  renderHistory();
  renderPreview();
  renderError();
  renderSubmitState();

  void Promise.all([
    lekhxApi.health().then((res) => {
      state.health = res;
      updateHeaderBadges();
    }),
    lekhxApi.languages().then((res) => {
      state.languages = res.languages || [];
      renderLanguages();
    }),
    lekhxApi.documents().then((res) => {
      state.history = res.documents || [];
      renderHistory();
    }),
    refreshTemplates(),
  ]).catch((err) => {
    state.error =
      err instanceof Error
        ? `Backend API unavailable (${err.message}). Start FastAPI with 'npm run api:dev'.`
        : "Backend API unavailable.";
    renderError();
  });

  return main;
}
