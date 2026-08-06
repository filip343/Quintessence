/**
 * Game state. All of it — the rules of play, none of the chemistry.
 *
 * Two decisions carried over from the terminal version, both of which changed
 * how the game feels:
 *
 * - **One move, one product.** A triprotic acid with a base gives three salts
 *   and the engine offers all of them, because it has no amounts. Taking all
 *   three would hand over three species for one move and score a way nobody
 *   chose, so a multi-product mix pauses for a choice.
 * - **The target is a trophy, not a reagent.** `Na2SO4 + H2SO4 -> NaHSO4` then
 *   `NaHSO4 + NaOH -> Na2SO4` is two real reactions and a fake way: it consumes
 *   the target to make the target. Any route needing the target is circular, so
 *   refusing it as an input costs no legitimate route.
 */

import type { PuzzleBundle, ReactionRecord } from "./puzzle";
import { missFor, reactionsFor } from "./puzzle";

/** A move as it is written down: what went in, and which product was taken. */
export interface Move {
  substrates: string[];
  /** The balanced equation, which identifies the chosen product uniquely. */
  equation: string;
}

export interface GameState {
  inventory: string[];
  /** Rule slug -> the player's own reaction for it. Insertion order = found order. */
  found: Record<string, ReactionRecord>;
  order: string[];
  /**
   * Every move that landed, in order. This is the only thing worth persisting:
   * replaying it rebuilds the rest, and replaying goes through this same
   * reducer, so a restored game is validated by the code that validated it
   * live. Storing `inventory` instead would let anyone paste in any species.
   */
  log: Move[];
  /** Every reaction that ran, newest last. The left-hand column. */
  made: ReactionRecord[];
  /**
   * Pairs that did nothing, deduplicated. The right-hand column — worth
   * keeping rather than discarding, because "these two do not react" is
   * knowledge the player earned and should not have to rediscover.
   */
  failed: string[][];
  selected: string[];
  /** Set when a mix offers more than one product and needs a decision. */
  pending: ReactionRecord[] | null;
  last: { reaction: ReactionRecord; scored: boolean; repeat: boolean } | null;
  message: string | null;
  moves: number;
  misses: number;
  revealed: boolean;
  /**
   * How much of a saved game survived replay, once one has been loaded. Kept in
   * game state rather than beside it so restoring is a single dispatch — a
   * `setState` inside the load effect would cascade an extra render.
   */
  restored: { kept: number; total: number } | null;
  /**
   * Whether the how-to-play cards are up. Here for the same reason as
   * `restored`: whether to teach is decided by the same look at storage that
   * decides what to replay, and routing it through the reducer keeps that one
   * dispatch instead of a dispatch plus a `setState`.
   */
  teaching: boolean;
}

export type Action =
  | { type: "select"; formula: string }
  | { type: "clear" }
  | { type: "mix" }
  | { type: "decompose"; formula: string }
  | { type: "choose"; index: number }
  | { type: "cancel" }
  | { type: "reveal" }
  | { type: "teach"; on: boolean }
  | { type: "restore"; state: GameState }
  | { type: "reset" };

export function initial(bundle: PuzzleBundle): GameState {
  return {
    inventory: [...bundle.palette],
    found: {},
    order: [],
    log: [],
    made: [],
    failed: [],
    selected: [],
    pending: null,
    last: null,
    message: null,
    moves: 0,
    misses: 0,
    revealed: false,
    restored: null,
    teaching: false,
  };
}

export function won(state: GameState, bundle: PuzzleBundle): boolean {
  return state.order.length >= bundle.want;
}

export function reducer(
  bundle: PuzzleBundle,
  state: GameState,
  action: Action,
): GameState {
  // Reading the rules is not a move, so it is answered above the guard below:
  // someone who has given up is exactly the person who might want to check what
  // they were meant to be doing.
  if (action.type === "teach") return { ...state, teaching: action.on };

  // Giving up ends the day. Once every way is printed on the screen there is
  // nothing left to find, and a reaction run now is copied off the page rather
  // than worked out — it would fill the rack with ways the player was handed.
  // The rule lives here rather than in the component so there is one answer to
  // "is this game still running", and so hiding the bench is presentation
  // rather than enforcement.
  if (state.revealed && action.type !== "reset" && action.type !== "restore") {
    return state;
  }

  switch (action.type) {
    case "select":
      return select(state, bundle, action.formula);

    case "clear":
      return { ...state, selected: [], message: null };

    case "cancel":
      return { ...state, pending: null, message: null };

    case "reveal":
      return {
        ...state,
        revealed: true,
        pending: null,
        selected: [],
        last: null,
        message: null,
      };

    case "restore":
      return action.state;

    case "reset":
      return initial(bundle);

    case "mix": {
      if (state.selected.length !== 2) return state;
      const [a, b] = state.selected;
      return offer(state, bundle, reactionsFor(bundle, a, b), `${a} + ${b}`, [a, b]);
    }

    case "decompose":
      return offer(
        state,
        bundle,
        reactionsFor(bundle, action.formula),
        `heating ${action.formula}`,
        [action.formula],
      );

    case "choose": {
      const chosen = state.pending?.[action.index];
      if (!chosen) return state;
      return apply({ ...state, pending: null }, bundle, chosen);
    }
  }
}

function select(
  state: GameState,
  bundle: PuzzleBundle,
  formula: string,
): GameState {
  if (formula === bundle.target) {
    return {
      ...state,
      message: `${bundle.target} is what you are making — a route that consumes it is not a way to make it.`,
    };
  }
  if (state.selected.includes(formula)) {
    return {
      ...state,
      selected: state.selected.filter((f) => f !== formula),
      message: null,
    };
  }
  // Selecting a third replaces the older of the two, so the board never locks.
  const selected = [...state.selected, formula].slice(-2);
  return { ...state, selected, message: null, last: null };
}

function offer(
  state: GameState,
  bundle: PuzzleBundle,
  reactions: ReactionRecord[],
  what: string,
  substrates: string[],
): GameState {
  if (reactions.length === 0) {
    const pair = [...substrates].sort();
    const known = state.failed.some(
      (seen) => seen.length === pair.length && seen.every((f, i) => f === pair[i]),
    );
    // Only some dead ends have a reason worth giving — see `missFor`. The pair
    // is kept in `failed` either way, so the note is looked up rather than
    // stored: it is a fact about the bundle, not about this game.
    const why = pair.length === 2 ? missFor(bundle, pair[0], pair[1]) : null;
    return {
      ...state,
      selected: [],
      pending: null,
      last: null,
      failed: known ? state.failed : [...state.failed, pair],
      misses: state.misses + 1,
      message: why ? `${what} — no reaction. ${why}.` : `${what} — no reaction.`,
    };
  }
  if (reactions.length === 1) return apply(state, bundle, reactions[0]);
  return { ...state, pending: reactions, message: null, last: null };
}

function apply(
  state: GameState,
  bundle: PuzzleBundle,
  reaction: ReactionRecord,
): GameState {
  const inventory = [...state.inventory];
  for (const product of reaction.products) {
    if (!inventory.includes(product)) inventory.push(product);
  }

  const makesTarget = reaction.products.includes(bundle.target);
  const repeat = makesTarget && reaction.rule in state.found;
  const scored = makesTarget && !repeat;

  return {
    ...state,
    inventory,
    found: scored ? { ...state.found, [reaction.rule]: reaction } : state.found,
    order: scored ? [...state.order, reaction.rule] : state.order,
    log: [
      ...state.log,
      { substrates: reaction.substrates, equation: reaction.equation },
    ],
    made: [...state.made, reaction],
    selected: [],
    pending: null,
    last: { reaction, scored, repeat },
    message: null,
    moves: state.moves + 1,
  };
}

/**
 * Rebuild a game by replaying moves through this same reducer.
 *
 * Every move has to survive the live rules to be applied: the substrates must
 * already be in hand, the pair must actually react, and the equation must be
 * one the bundle offers for that pair. A move that fails any of those stops the
 * replay — the log is causally ordered, so once one step is impossible the rest
 * describes a game that never happened.
 *
 * The security property falls out of that: nothing is trusted except the fact
 * that a move was attempted, and the bundle decides what a move does.
 */
export function replay(
  bundle: PuzzleBundle,
  moves: Move[],
): { state: GameState; replayed: number } {
  let state = initial(bundle);

  for (const [index, move] of moves.entries()) {
    const [a, b] = move.substrates;
    if (!a || !state.inventory.includes(a)) return { state, replayed: index };
    if (b !== undefined && !state.inventory.includes(b)) {
      return { state, replayed: index };
    }

    let next =
      b === undefined
        ? reducer(bundle, state, { type: "decompose", formula: a })
        : reducer(
            bundle,
            reducer(bundle, reducer(bundle, state, { type: "select", formula: a }), {
              type: "select",
              formula: b,
            }),
            { type: "mix" },
          );

    if (next.pending) {
      const choice = next.pending.findIndex((r) => r.equation === move.equation);
      if (choice < 0) return { state, replayed: index };
      next = reducer(bundle, next, { type: "choose", index: choice });
    }

    // Either the pair did not react, or it produced something else entirely.
    if (next.log.length !== state.log.length + 1) return { state, replayed: index };
    if (next.log[next.log.length - 1].equation !== move.equation) {
      return { state, replayed: index };
    }
    state = next;
  }

  return { state: { ...state, last: null, selected: [] }, replayed: moves.length };
}

/**
 * Keep only the saved dead ends that are still dead ends.
 *
 * Failures change no game state, so they are not part of the replay — but they
 * come out of storage all the same, and anything out of storage gets checked.
 * A pair survives only if the player could really have tried it (both species
 * in hand) and it really does nothing.
 */
export function validFailures(
  bundle: PuzzleBundle,
  state: GameState,
  pairs: string[][],
): string[][] {
  const seen = new Set<string>();
  return pairs.filter((pair) => {
    if (pair.length < 1 || pair.length > 2) return false;
    if (pair.some((formula) => !state.inventory.includes(formula))) return false;
    if (pair.includes(bundle.target)) return false;
    const [a, b] = pair;
    if (reactionsFor(bundle, a, b).length > 0) return false;
    const key = [...pair].sort().join("+");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
