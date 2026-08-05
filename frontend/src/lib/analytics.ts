/**
 * Four numbers: who is here, who is new, who solved it, and how long a run
 * they are on.
 *
 * Umami identifies a visitor by hashing the request against a salt that
 * rotates monthly, so its own notion of a person dissolves every month and no
 * report it offers can follow a streak across one. Rather than work around
 * that, the browser answers the question itself — the streak is game state we
 * already keep — and ships the answer as a property on the event. Umami then
 * only has to count, which is the thing it is good at.
 *
 * Which is also why there is no `umami.identify()` here and no analytics id
 * anywhere. Everything sent is a number the game already knew; nothing sent
 * says who sent it. That keeps the storage this game uses strictly functional
 * — saves, theme, streak — and a puzzle nobody pays for should not be greeting
 * people with a consent banner.
 *
 * The tracker is loaded deferred and is blocked outright by most content
 * blockers, so `window.umami` may never appear. Every call here is a no-op in
 * that case, which is also what makes this file safe to ship before the site
 * is hosted: without a website id there is no script, and nothing happens.
 */

declare global {
  interface Window {
    umami?: {
      track: (event: string, data?: Record<string, unknown>) => void;
    };
  }
}

/** Roughly five seconds, in half-second tries. */
const ATTEMPTS = 10;
const RETRY_MS = 500;

function send(
  event: string,
  data: Record<string, unknown> | undefined,
  attempt: number,
): void {
  const umami = window.umami;
  if (umami) {
    try {
      umami.track(event, data);
    } catch {
      // A beacon is never worth an exception in a game loop.
    }
    return;
  }
  // Not there yet, or not coming. Most events here follow minutes of play and
  // find the tracker loaded, but `first-visit` fires from a mount effect and
  // genuinely races a deferred script, so it is worth waiting out. After the
  // last try, assume blocked and drop it.
  if (attempt >= ATTEMPTS) return;
  window.setTimeout(() => send(event, data, attempt + 1), RETRY_MS);
}

export function track(event: string, data?: Record<string, unknown>): void {
  if (typeof window === "undefined") return;
  send(event, data, 0);
}
