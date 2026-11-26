(() => {
  const storageKey = "forgeai.theme";
  const choices = ["light", "dark", "system"];
  const darkScheme = window.matchMedia?.("(prefers-color-scheme: dark)");
  let preference = "system";

  try {
    const saved = localStorage.getItem(storageKey);
    if (choices.includes(saved)) preference = saved;
  } catch {
    // Theme changes also work when browser storage is unavailable.
  }

  function applyTheme() {
    const theme = preference === "system" ? (darkScheme?.matches ? "dark" : "light") : preference;
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#151124" : "#f6f4fa");
    for (const control of document.querySelectorAll("[data-theme-choice]")) {
      control.setAttribute("aria-pressed", String(control.dataset.themeChoice === preference));
    }
  }

  applyTheme();
  document.addEventListener("DOMContentLoaded", applyTheme, { once: true });
  darkScheme?.addEventListener?.("change", applyTheme);
  document.addEventListener("click", (event) => {
    const control = event.target.closest("[data-theme-choice]");
    if (!control || !choices.includes(control.dataset.themeChoice)) return;
    preference = control.dataset.themeChoice;
    try {
      localStorage.setItem(storageKey, preference);
    } catch {
      // The current tab still uses the selected theme.
    }
    applyTheme();
  });
})();
