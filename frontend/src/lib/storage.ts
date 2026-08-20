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

const PREFIX = "quintessence";

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
  /**
   * Whether the solved window has been answered with *keep hunting*. Optional
   * so that adding it costs nothing: a save written before it existed reads as
   * `undefined`, which is the same as not having answered — and re-offering the
   * choice is the harmless failure of the two. Bumping `SAVE_VERSION` for it
   * would have thrown away every game in progress to save one reload.
   */
  hunting?: boolean;
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

/**
 * `decisions` is an object rather than two more positional arguments because
 * both are booleans, and `store(day, bundle, moves, failed, true, false)` is a
 * line nobody can read twice and be sure about.
 */
export function store(
  day: string,
  bundle: PuzzleBundle,
  moves: Move[],
  failed: string[][],
  decisions: { revealed: boolean; hunting: boolean },
): void {
  if (typeof window === "undefined") return;
  const save: Save = {
    version: SAVE_VERSION,
    day,
    target: bundle.target,
    moves,
    failed,
    revealed: decisions.revealed,
    hunting: decisions.hunting,
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

const STREAK_KEY = `${PREFIX}:streak`;

export interface Streak {
  /** The last puzzle day counted towards the run, `YYYY-MM-DD`. */
  last: string;
  current: number;
  best: number;
}

/**
 * The run of consecutive daily puzzles solved.
 *
 * Its own key, not a field on `Save`: a streak outlives any one day, and
 * putting it on the save would mean bumping `SAVE_VERSION`, which drops every
 * game in progress. It is real game state rather than bookkeeping — a badge
 * wants it as much as the analytics do.
 *
 * Per-browser and permanently so. Clearing storage or moving to a phone loses
 * the run, which is what a game with no accounts costs; carrying it would take
 * a login and a server, and this game has neither by design.
 */
export function readStreak(): Streak | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STREAK_KEY);
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null) return null;
    const streak = value as Partial<Streak>;
    if (
      typeof streak.last !== "string" ||
      typeof streak.current !== "number" ||
      typeof streak.best !== "number"
    ) {
      return null;
    }
    return { last: streak.last, current: streak.current, best: streak.best };
  } catch {
    return null;
  }
}

/** The previous calendar day. UTC throughout, so no clock change can skip one. */
function dayBefore(day: string): string | null {
  const time = Date.parse(`${day}T00:00:00Z`);
  if (Number.isNaN(time)) return null;
  return new Date(time - 86_400_000).toISOString().slice(0, 10);
}

/**
 * Count a solved day, and return the run it leaves.
 *
 * Only ever moves forward: a day at or before `last` changes nothing. That is
 * what makes playing the archive harmless — going back to finish Tuesday
 * cannot reset the run you are on, and cannot extend it either. Dates compare
 * as strings because they are ISO.
 */
export function recordSolve(day: string): Streak {
  const previous = readStreak();
  const fresh: Streak = { last: day, current: 1, best: 1 };
  if (!previous) return writeStreak(fresh);
  if (day <= previous.last) return previous;

  const current = dayBefore(day) === previous.last ? previous.current + 1 : 1;
  return writeStreak({
    last: day,
    current,
    best: Math.max(previous.best, current),
  });
}

function writeStreak(streak: Streak): Streak {
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(STREAK_KEY, JSON.stringify(streak));
    } catch {
      // Storage off. The run is not recoverable, but play is unaffected.
    }
  }
  return streak;
}

/**
 * The run as it stands *now*, which is not the same as the number on disk.
 *
 * `recordSolve` only ever runs when a day is solved, so nothing writes down
 * that a run has ended — miss two days and storage still says "3". The stored
 * number is the length of the run at its last solve; whether that run is still
 * alive is a question about the clock, and only the reader has the clock.
 *
 * Alive means the last solve was today or yesterday. Yesterday counts because
 * today is still playable: that is the state a streak display exists for.
 */
export function currentStreak(streak: Streak | null, today: string): number {
  if (!streak) return 0;
  if (streak.last === today || streak.last === dayBefore(today)) {
    return streak.current;
  }
  return 0;
}

const RESULTS_KEY = `${PREFIX}:results`;

export interface Result {
  /** Whether every kind the day asked for was found. */
  solved: boolean;
  /** Kinds found. May exceed the ask — bonus ways are counted here too. */
  ways: number;
  moves: number;
}

/**
 * How each finished day went, one entry per day.
 *
 * Its own key for the same reason the streak has one: it outlives any single
 * day, so putting it on a save would mean bumping `SAVE_VERSION` and dropping
 * every game in progress. Nothing derived from a save is stored -- a save is
 * still only a move log -- because this is a different question. A save answers
 * "where was I", and replaying it is the honest way to find out; this answers
 * "what have I done", which no single save can, and which the home page would
 * otherwise have to reconstruct by replaying a year of them.
 *
 * Bounded by the number of days that exist, so it cannot run away.
 */
export function readResults(): Record<string, Result> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(RESULTS_KEY);
    if (!raw) return {};
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null) return {};
    const results: Record<string, Result> = {};
    for (const [day, result] of Object.entries(value as Record<string, unknown>)) {
      if (isResult(result)) results[day] = result;
    }
    return results;
  } catch {
    return {};
  }
}

/**
 * Write down how a day ended. The first outcome for a day is the one that
 * counts, matching `claimOutcome` -- someone who gives up, starts over and then
 * solves it has read the answer sheet, and the ledger should not say otherwise.
 */
export function recordResult(day: string, result: Result): void {
  if (typeof window === "undefined") return;
  const results = readResults();
  if (day in results) return;
  try {
    window.localStorage.setItem(
      RESULTS_KEY,
      JSON.stringify({ ...results, [day]: result }),
    );
  } catch {
    // Storage off or full. The day still played; it just goes uncounted.
  }
}

function isResult(value: unknown): value is Result {
  if (typeof value !== "object" || value === null) return false;
  const result = value as Partial<Result>;
  return (
    typeof result.solved === "boolean" &&
    typeof result.ways === "number" &&
    typeof result.moves === "number"
  );
}

/**
 * True the first time it is asked for a given key, false ever after.
 *
 * Everything reported here is reported once, and the guard has to be written
 * down rather than held in state: a save is replayed through the reducer on
 * every load, so a solved game is freshly "just solved" on each reload, and a
 * tab left open all week would otherwise count as a week of solvers.
 *
 * Storage off means it cannot remember, and it answers yes — a refresh may
 * double-count that browser, which is a smaller distortion than dropping
 * private-mode players from the numbers entirely.
 */
function claimOnce(name: string): boolean {
  if (typeof window === "undefined") return false;
  const slot = `${PREFIX}:sent:${name}`;
  try {
    if (window.localStorage.getItem(slot)) return false;
    window.localStorage.setItem(slot, "1");
    return true;
  } catch {
    return true;
  }
}

/**
 * Claim the right to report how a day ended.
 *
 * One outcome per day, whichever happens first — a player who gives up, starts
 * over and then solves it has read the answer sheet, and neither the solve
 * count nor their streak should pretend otherwise. `start over` deliberately
 * does not release the claim; that is the hole it exists to close.
 */
export function claimOutcome(day: string): boolean {
  return claimOnce(day);
}

export function claimFirstVisit(): boolean {
  return claimOnce("first-visit");
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
    (save.hunting === undefined || typeof save.hunting === "boolean") &&
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
