/**
 * EPS PHOENIX — THEME & APPEARANCE ENGINE
 * Compliant with Section 20 (ChatGPT Appearance settings reference)
 * Handles System/Light/Dark mode, contrast, and font size persistence.
 */

(function () {
  const THEME_KEY = "eps_phoenix_theme";
  const CONTRAST_KEY = "eps_phoenix_contrast";
  const ACCENT_KEY = "eps_phoenix_accent";

  function getStoredTheme() {
    return localStorage.getItem(THEME_KEY) || "system";
  }

  function applyTheme(theme) {
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);

    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.classList.toggle("dark", prefersDark);
    } else if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }

  function applyContrast(contrast) {
    if (contrast === "high") {
      document.documentElement.setAttribute("data-contrast", "high");
    } else {
      document.documentElement.removeAttribute("data-contrast");
    }
  }

  function applyAccent(accent) {
    if (accent) {
      document.documentElement.style.setProperty("--color-accent", accent);
    }
  }

  // Initialize immediately on script execution to prevent FOUC (Flash of Unstyled Content)
  const initialTheme = getStoredTheme();
  applyTheme(initialTheme);
  applyContrast(localStorage.getItem(CONTRAST_KEY) || "standard");
  applyAccent(localStorage.getItem(ACCENT_KEY));

  // Listen for system theme changes if set to system
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (getStoredTheme() === "system") {
      document.documentElement.classList.toggle("dark", e.matches);
    }
  });

  // Global helper on window
  window.EPSAppearance = {
    setTheme: function (theme) {
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
    },
    getTheme: getStoredTheme,
    setContrast: function (contrast) {
      localStorage.setItem(CONTRAST_KEY, contrast);
      applyContrast(contrast);
    },
    setAccent: function (accentHex) {
      localStorage.setItem(ACCENT_KEY, accentHex);
      applyAccent(accentHex);
    },
  };
})();
