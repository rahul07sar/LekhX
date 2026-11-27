import { createAppShell } from "./layout/AppShell.js";
import { renderHome } from "./pages/home.js";

const appState = Object.freeze({
  appName: "LekhX",
  version: "1.0.0",
  huggingfaceRepo: "drishtijs/LekhX",
});

function mount() {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return;
  }
  const root = document.getElementById("app");
  if (!root) {
    throw new Error("#app root element not found");
  }
  const page = renderHome(appState);
  root.replaceChildren(createAppShell(appState, page));
}

mount();
