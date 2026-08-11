/**
 * A player's report, and the state that makes it worth reading.
 *
 * "A reaction looked wrong" is not a bug report. "2026-08-11, PbSO3, I mixed
 * Na2O and H2O and got this equation" is one, because it turns into
 * `python -m chem.puzzle 2026-08-11` and a diff. Nobody can type that
 * accurately from memory and nobody should have to, so the page assembles it —
 * the day, the target, the bundle it was dealt from, and the move log, which
 * the save already keeps for exactly this kind of replay.
 *
 * It is built here as the finished string rather than as an object the server
 * renders, because the dialog shows this exact text before anything is sent.
 * Attaching a move log to someone's message on their behalf is only honest if
 * they can see what they are attaching, and it keeps this file consistent with
 * the line `analytics.ts` takes: nothing leaves the browser unannounced.
 *
 * The limits are shared with `app/api/report/route.ts` rather than duplicated.
 * The endpoint is public and re-checks all of them — these are here to keep the
 * dialog from offering to send something that would only be refused.
 */

import type { GameState } from "./game";
import type { PuzzleBundle } from "./puzzle";

export const KINDS = ["chemistry", "bug", "idea"] as const;
export type Kind = (typeof KINDS)[number];

/** What each kind is called on the button. Lower case, like the rest of the chrome. */
export const KIND_LABELS: Record<Kind, string> = {
  chemistry: "wrong chemistry",
  bug: "something broke",
  idea: "suggestion",
};

export const MESSAGE_LIMIT = 2000;
export const CONTACT_LIMIT = 200;
export const CONTEXT_LIMIT = 8000;

export interface Report {
  kind: Kind;
  message: string;
  /** Optional. Without it a report is anonymous and cannot be replied to. */
  contact: string;
  context: string;
}

/**
 * Where the report came from. Every field is optional: a report that the
 * calendar failed to load is exactly the one with the least to attach, and
 * refusing it would be the wrong way round.
 */
export interface Subject {
  day: string | null;
  bundle: PuzzleBundle | null;
  state: GameState | null;
}

const EMPTY: Subject = { day: null, bundle: null, state: null };

/**
 * What the button would attach if it were pressed right now.
 *
 * A module-level slot rather than a context, and deliberately so. The button
 * lives in the root layout because it has to be on every page, so it is a
 * sibling of the page rather than a descendant and cannot be handed props. The
 * alternative — a provider holding this in state — would re-render the whole
 * tree beneath it on every move, to feed a value nothing reads until somebody
 * opens the panel. A slot written by an effect costs nothing and is read once.
 *
 * There is exactly one game on screen at a time, which is what makes a single
 * slot the right shape rather than a shortcut.
 */
let subject: Subject = EMPTY;

/**
 * Publish this page's subject, and get back the cleanup that retracts it.
 *
 * The identity check is what makes it safe on a route change: React mounts the
 * incoming page before it unmounts the outgoing one, so a cleanup that cleared
 * unconditionally would wipe the new page's subject a moment after it was set.
 * Clearing only what is still current means the last writer wins, which is
 * also the truth — it is the page you are looking at.
 */
export function publish(next: Subject): () => void {
  subject = next;
  return () => {
    if (subject === next) subject = EMPTY;
  };
}

export function current(): Subject {
  return subject;
}

export function attachment({ day, bundle, state }: Subject): string {
  const lines: string[] = [];

  if (typeof window !== "undefined") {
    lines.push(`page      ${window.location.pathname}`);
  }
  if (day) lines.push(`day       ${day}`);

  if (bundle) {
    lines.push(`target    ${bundle.target}  ${bundle.name}`);
    lines.push(
      `puzzle    ${bundle.grade}, asking ${bundle.want} of ${bundle.ways} ways,` +
        ` cut ${bundle.cut}, bundle v${bundle.version}`,
    );
  } else {
    lines.push("puzzle    none loaded");
  }

  if (state) {
    // Rule slugs, not the display names: the reader of this is the person with
    // `chem.rules.catalogue` open, and the slug is what that file is keyed on.
    lines.push(
      `found     ${state.order.length}` +
        (state.order.length ? ` — ${state.order.join(", ")}` : ""),
    );
    lines.push(
      `moves     ${state.moves}, ${state.misses} dead ends` +
        (state.revealed ? ", gave up" : ""),
    );
    if (state.log.length) {
      lines.push("log");
      for (const [index, move] of state.log.entries()) {
        lines.push(`  ${String(index + 1).padStart(2)}  ${move.equation}`);
      }
    }
  }

  // Standard for a "something broke" report and useless for anything else, but
  // it is on screen with the rest before it goes anywhere, which is the whole
  // basis on which any of this is attached.
  if (typeof navigator !== "undefined") {
    lines.push(`browser   ${navigator.userAgent}`);
  }

  return lines.join("\n").slice(0, CONTEXT_LIMIT);
}

export type Outcome = "sent" | "unconfigured" | "failed";

/**
 * Post a report. Never throws — a failed report is a message to show, not an
 * exception to handle, and the dialog keeps the typed text either way so a
 * retry costs nothing.
 *
 * `unconfigured` is its own outcome rather than a failure because it is the
 * normal state of a local checkout with no Resend key, and telling someone
 * their report failed when the machine was never set up to send one is the
 * kind of thing that gets reported.
 */
export async function submit(report: Report): Promise<Outcome> {
  try {
    const response = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    });
    if (response.ok) return "sent";
    if (response.status === 503) return "unconfigured";
    return "failed";
  } catch {
    return "failed"; // offline, blocked, or the endpoint is not there
  }
}
