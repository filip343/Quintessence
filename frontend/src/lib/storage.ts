/**
 * Saving a game in progress.
 *
 * Only the move log is written. Everything else — inventory, which ways you
 * have found, the move count — is derived by replaying that log through the
 * reducer on load, which means a restored game passes through exactly the
 * checks a live one does. Persisting the derived state instead would make the
 * inventory a free-text field: paste in any formula and the game would believe
 * it.
 *
 * This protects the *integrity* of a game, not the secrecy of its answers. The
 * bundle ships `answers` to the browser deliberately, so the end screen works
 * offline; anyone who opens devtools can read them. What this stops is a save
 * that puts species into play the puzzle never contained.
 */

import type { Move } from "./game";
import type { PuzzleBundle } from "./puzzle";

const PREFIX = "fiveways";

/** Bumped when the save shape changes, so old saves are dropped not misread. */
const SAVE_VERSION = 1;

export interface Save {
  version: number;
  day: string;
  /** Guards against the day being regenerated under a save. */
  target: string;
  moves: Move[];
  /** Dead ends worth remembering. Re-checked on load, never trusted. */
  failed: string[][];
  revealed: boolean;
}

function key(day: string): string {
  return `${PREFIX}:${day}`;
}

export function load(day: string, bundle: PuzzleBundle): Save | null {
  if (typeof window === "undefined") return null;
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(key(day));
  } catch {
    return null; // private mode, storage disabled — play unsaved
  }
  if (!raw) return null;

  try {
    const save: unknown = JSON.parse(raw);
    if (!isSave(save)) return null;
    // A regenerated puzzle is a different puzzle even on the same date.
    if (save.version !== SAVE_VERSION || save.day !== day) return null;
    if (save.target !== bundle.target) return null;
    return save;
  } catch {
    return null;
  }
}

export function store(
  day: string,
  bundle: PuzzleBundle,
  moves: Move[],
  failed: string[][],
  revealed: boolean,
): void {
  if (typeof window === "undefined") return;
  const save: Save = {
    version: SAVE_VERSION,
    day,
    target: bundle.target,
    moves,
    failed,
    revealed,
  };
  try {
    window.localStorage.setItem(key(day), JSON.stringify(save));
  } catch {
    // Quota or disabled storage. Losing a save is not worth breaking play over.
  }
}

const TUTORIAL_KEY = `${PREFIX}:tutorial`;

/**
 * Whether this browser has been shown how to play.
 *
 * Its own key rather than a field on the save, because it outlives any one day
 * and has to survive "start over" — someone clearing today's board is not
 * asking to be taught the rules again.
 *
 * `null` means "cannot tell": storage is off, so the caller decides. It must
 * not be read during render — on the server there is no `localStorage`, and
 * seeding state from it would be a hydration mismatch.
 */
export function tutorialSeen(): boolean | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TUTORIAL_KEY) === "1";
  } catch {
    return null;
  }
}

export function markTutorialSeen(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TUTORIAL_KEY, "1");
  } catch {
    // Storage off. They will be offered the tutorial again next visit, which
    // is the kinder failure of the two.
  }
}

export function clear(day: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(key(day));
  } catch {
    // ignore
  }
}

/** Shape check only — the reducer decides whether the moves are *legal*. */
function isSave(value: unknown): value is Save {
  if (typeof value !== "object" || value === null) return false;
  const save = value as Partial<Save>;
  return (
    typeof save.version === "number" &&
    typeof save.day === "string" &&
    typeof save.target === "string" &&
    typeof save.revealed === "boolean" &&
    Array.isArray(save.failed) &&
    save.failed.every(
      (pair) => Array.isArray(pair) && pair.every((f) => typeof f === "string"),
    ) &&
    Array.isArray(save.moves) &&
    save.moves.every(
      (move) =>
        typeof move === "object" &&
        move !== null &&
        typeof (move as Move).equation === "string" &&
        Array.isArray((move as Move).substrates) &&
        (move as Move).substrates.length >= 1 &&
        (move as Move).substrates.length <= 2 &&
        (move as Move).substrates.every((s) => typeof s === "string"),
    )
  );
}
