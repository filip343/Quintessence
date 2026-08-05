"use client";

/**
 * Light / dark, in the corner.
 *
 * The icon never changes with the theme, which is what keeps this component
 * stateless: there is nothing to read on the server, nothing to get wrong on
 * hydration, and no flash of the wrong glyph. A half-filled circle means
 * "switch how this looks" in either direction, so it does not need to.
 *
 * The current theme is read back from the resolved `color-scheme` rather than
 * from storage, so the first click does the right thing whether the page is
 * dark because the OS says so or because a previous visit said so.
 */

const KEY = "fiveways:theme";

export function ThemeToggle() {
  function flip() {
    const root = document.documentElement;
    const dark = getComputedStyle(root).colorScheme.includes("dark");
    const next = dark ? "light" : "dark";
    root.dataset.theme = next;
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      // Storage off. The theme still flips, it just will not be remembered.
    }
  }

  return (
    <button
      type="button"
      onClick={flip}
      title="Switch between light and dark"
      aria-label="Switch between light and dark"
      className="panel fixed top-4 right-4 z-50 rounded-full border p-2.5 text-muted transition-[color,transform] duration-150 hover:-translate-y-px hover:text-ink"
    >
      <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
        <circle
          cx="10"
          cy="10"
          r="7.25"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path d="M10 2.75a7.25 7.25 0 0 0 0 14.5z" fill="currentColor" />
      </svg>
    </button>
  );
}
