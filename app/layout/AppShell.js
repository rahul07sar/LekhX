export function createAppShell(state, page) {
  const shell = document.createElement("div");
  shell.className = "lekhx-shell";

  const header = document.createElement("header");
  header.className = "lekhx-topbar";

  const brand = document.createElement("a");
  brand.className = "lekhx-brand";
  brand.href = "/";

  const logo = document.createElement("img");
  logo.src = "/public/logo.svg";
  logo.alt = "LekhX logo";

  const brandTextWrap = document.createElement("div");
  const titleEl = document.createElement("strong");
  titleEl.textContent = (state && state.appName) || "LekhX";
  const subEl = document.createElement("div");
  subEl.className = "lekhx-brand-sub";
  subEl.textContent = "Offline Multilingual Office Generator (DrishtiJS)";
  brandTextWrap.append(titleEl, subEl);
  brand.append(logo, brandTextWrap);

  const badgeRow = document.createElement("div");
  badgeRow.className = "lekhx-badges";
  badgeRow.id = "lekhx-status-badges";

  const datasetPill = document.createElement("span");
  datasetPill.className = "lekhx-pill";
  datasetPill.textContent = "HF Dataset: drishtijs/LekhX";
  badgeRow.appendChild(datasetPill);

  header.append(brand, badgeRow);
  shell.append(header, page);
  return shell;
}
