/**
 * Which day the game is on, and how long until the next one.
 *
 * **UTC, not local time.** Everyone gets the same compound at the same instant,
 * which is what lets two people compare a score without first agreeing on whose
 * midnight counts.
 *
 * This lives in its own file because the home page and the board have to answer
 * the same question and must not answer it differently — two implementations of
 * "what day is it" is the sort of disagreement that surfaces as a countdown to
 * a puzzle that is already playable.
 */

/** The UTC date, `YYYY-MM-DD`. The one clock the whole game agrees on. */
export function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * The most recent day that is not in the future.
 *
 * Falling back to the earliest day rather than to nothing is deliberate: a
 * calendar that has run out should keep serving a playable puzzle instead of an
 * error page. `verify_bundles.py` is what notices the runway is short, because
 * that is a job for CI and not for a player's browser.
 */
export function pick(days: string[], now: string): string | undefined {
  const sorted = [...days].sort();
  const available = sorted.filter((day) => day <= now);
  return available.at(-1) ?? sorted.at(0);
}

/**
 * The next day on the calendar after the one being served.
 *
 * Keyed on the day being played rather than on the clock, so a calendar that
 * has run out reports no next puzzle at all instead of counting down to a
 * midnight that will bring nothing.
 */
export function after(days: string[], current: string): string | undefined {
  return [...days].sort().find((day) => day > current);
}

/** Milliseconds from `from` until a day's UTC midnight. Negative once past. */
export function until(day: string, from: number): number {
  return Date.parse(`${day}T00:00:00Z`) - from;
}

/** A duration the way a countdown is read. */
export function countdown(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const pad = (n: number) => String(n).padStart(2, "0");
  const days = Math.floor(total / 86_400);
  const hours = Math.floor(total / 3_600) % 24;
  const minutes = Math.floor(total / 60) % 60;
  const seconds = total % 60;

  // Seconds are dropped past a day, where they are noise rather than tension.
  // Only a gap in the calendar gets there; the normal wait is under 24 hours.
  return days > 0
    ? `${days}d ${pad(hours)}h ${pad(minutes)}m`
    : `${pad(hours)}h ${pad(minutes)}m ${pad(seconds)}s`;
}
