(() => {
  const storageKey = "forgeai.theme";
  const choices = ["light", "dark", "system"];
  const darkScheme = window.matchMedia?.("(prefers-color-scheme: dark)");
  let preference = "system";

  try {
    const saved = localStorage.getItem(storageKey);
    if (choices.includes(saved)) preference = saved;
  } catch {
    // Storage may be blocked by browser settings.
  }

  function currentTheme() {
    return preference === "system" ? (darkScheme?.matches ? "dark" : "light") : preference;
  }

  function applyTheme() {
    const theme = currentTheme();
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#111112" : "#f7f5f5");
    for (const control of document.querySelectorAll("[data-theme-toggle]")) {
      control.setAttribute("aria-pressed", String(theme === "dark"));
      control.title = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
    }
    for (const control of document.querySelectorAll("[data-theme-choice]")) {
      control.setAttribute("aria-pressed", String(control.dataset.themeChoice === preference));
    }
  }

  applyTheme();
  document.addEventListener("DOMContentLoaded", applyTheme, { once: true });
  darkScheme?.addEventListener?.("change", applyTheme);
  document.addEventListener("click", (event) => {
    const control = event.target.closest("button[data-theme-toggle], button[data-theme-choice]");
    if (!control) return;
    const next = control.hasAttribute("data-theme-toggle")
      ? (currentTheme() === "dark" ? "light" : "dark")
      : control.dataset.themeChoice;
    if (!choices.includes(next)) return;
    preference = next;
    try {
      localStorage.setItem(storageKey, preference);
    } catch {}
    applyTheme();
  });
})();
