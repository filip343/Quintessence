"use client";

import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import type { PuzzleBundle, ReactionRecord } from "@/lib/puzzle";
import { missFor, reactionsFor, ruleName, speciesClass } from "@/lib/puzzle";
import {
  type Action,
  type GameState,
  initial,
  reducer,
  replay,
  validFailures,
  won,
} from "@/lib/game";
import {
  claimFirstVisit,
  claimOutcome,
  clear,
  load,
  markTutorialSeen,
  recordSolve,
  store,
  tutorialSeen,
} from "@/lib/storage";
import { track } from "@/lib/analytics";
import { Chip } from "./Chip";
import { Equation, Formula } from "./Formula";
import { Legend } from "./Legend";
import { Tutorial } from "./Tutorial";

const GRADE_NOTE: Record<string, string> = {
  easy: "several ways in easy reach",
  medium: "you will have to build something first",
  hard: "few ways exist, and none of them are obvious",
};

export function Game({ bundle, day }: { bundle: PuzzleBundle; day?: string }) {
  const [state, dispatch] = useReducer(
    (s: GameState, a: Action) => reducer(bundle, s, a),
    bundle,
    initial,
  );
  const complete = won(state, bundle);

  const hydrated = useRef(false);

  // Restore after mount rather than during render: localStorage does not exist
  // on the server, and seeding the reducer from it would be a hydration
  // mismatch. One dispatch, no setState — the replay result rides along in the
  // restored state.
  useEffect(() => {
    if (!day || hydrated.current) return;
    hydrated.current = true;

    const save = load(day, bundle);

    // First time here: nothing played, and no record of having been told how.
    // A save with moves in it means they are mid-game and know what this is,
    // so an overlay would only be in the way.
    const played = Boolean(save && (save.moves.length > 0 || save.revealed));
    const teaching = tutorialSeen() !== true && !played;

    // No save at all and no record of having been told how to play is as close
    // to "never been here" as a game without accounts can get. Reusing the
    // flags the tutorial already needs, rather than minting an id to count
    // people with.
    if (!save && teaching && claimFirstVisit()) track("first-visit");

    // Not `|| save.moves.length === 0`: a game whose whole story is "I gave up"
    // — or "these four pairs do nothing" — has an empty move log and still has
    // to come back. Replaying no moves is just the opening position.
    if (!save) {
      if (teaching) dispatch({ type: "teach", on: true });
      return;
    }

    const { state: rebuilt, replayed } = replay(bundle, save.moves);
    dispatch({
      type: "restore",
      state: {
        ...rebuilt,
        failed: validFailures(bundle, rebuilt, save.failed ?? []),
        revealed: save.revealed,
        restored: { kept: replayed, total: save.moves.length },
        teaching,
      },
    });
  }, [bundle, day]);

  useEffect(() => {
    if (!day || !hydrated.current) return;
    store(day, bundle, state.log, state.failed, state.revealed);
  }, [bundle, day, state.log, state.failed, state.revealed]);

  // How the day ended, reported once. The streak is counted here rather than
  // where the win is displayed so that the two can never disagree: one claim,
  // one bump, one event.
  useEffect(() => {
    if (!day || !hydrated.current) return;
    if (!complete && !state.revealed) return;
    if (!claimOutcome(day)) return;

    const shape = {
      day,
      grade: bundle.grade,
      moves: state.moves,
      ways: state.order.length,
    };
    if (complete) {
      track("solved", { ...shape, streak: recordSolve(day).current });
    } else {
      track("gave-up", shape);
    }
  }, [bundle.grade, complete, day, state.moves, state.order.length, state.revealed]);

  return (
    <main className="mx-auto flex w-full max-w-352 flex-col gap-7 px-4 py-8 sm:px-6">
      {state.teaching && (
        <Tutorial
          bundle={bundle}
          onClose={() => {
            markTutorialSeen();
            dispatch({ type: "teach", on: false });
          }}
        />
      )}

      <Header bundle={bundle} state={state} day={day} dispatch={dispatch} />

      {state.restored && state.restored.kept < state.restored.total && (
        <p className="rounded-lg border border-[color-mix(in_oklab,var(--brass)_40%,transparent)] bg-[color-mix(in_oklab,var(--brass)_10%,var(--panel))] px-4 py-3 text-sm">
          Kept {state.restored.kept} of {state.restored.total} saved moves. The rest
          could not be replayed against today&rsquo;s puzzle, so they were dropped.
        </p>
      )}

      {/*
        Three columns on a wide screen: what worked on the left, the bench in
        the middle, what did not on the right. The bench is what the eye should
        land on, so it keeps the centre and the histories fill the margins that
        were empty. Below `xl` they stack under the bench, ordered so the bench
        is still first.
      */}
      <div className="grid gap-6 xl:grid-cols-[17rem_minmax(0,1fr)_17rem] xl:items-start">
        <Trail
          title="reactions you ran"
          count={state.made.length}
          tone="flask"
          className="order-2 xl:order-1 xl:border-r xl:border-rule xl:pr-5"
        >
          {[...state.made].reverse().map((reaction, index) => (
            <li
              key={`${reaction.equation}-${index}`}
              className={[
                "rounded-md border px-2.5 py-1.5",
                index === 0
                  ? "panel border-rule"
                  : "border-transparent",
              ].join(" ")}
            >
              <Equation equation={reaction.equation} className="font-mono text-xs" />
              {reaction.note && (
                <div className="mt-0.5 text-[11px] text-muted">{reaction.note}</div>
              )}
            </li>
          ))}
        </Trail>

        <div className="order-1 flex flex-col gap-6 xl:order-2">
          {state.revealed ? (
            <Closed bundle={bundle} state={state} />
          ) : state.pending ? (
            <Picker reactions={state.pending} dispatch={dispatch} />
          ) : (
            <Bench bundle={bundle} state={state} dispatch={dispatch} />
          )}
          <Rack bundle={bundle} state={state} />
          <Legend />
        </div>

        <Trail
          title="no reaction"
          count={state.failed.length}
          tone="muted"
          className="order-3 xl:border-l xl:border-rule xl:pl-5"
        >
          {[...state.failed].reverse().map((pair) => {
            const why = pair.length === 2 ? missFor(bundle, pair[0], pair[1]) : null;
            return (
              <li key={pair.join("+")} className="rounded-md px-2.5 py-1.5">
                <span className="font-mono text-xs text-muted line-through decoration-rule">
                  {pair.map((formula, index) => (
                    <span key={formula}>
                      {index > 0 && <span className="mx-1 no-underline">+</span>}
                      <Formula formula={formula} />
                    </span>
                  ))}
                </span>
                {/* Struck through above, deliberately not here: the pair is
                    spent, but the reason is the part worth reading twice. */}
                {why && (
                  <span className="mt-0.5 block text-[11px] leading-snug text-muted">
                    {why}
                  </span>
                )}
              </li>
            );
          })}
        </Trail>
      </div>

      {(complete || state.revealed) && <Answers bundle={bundle} state={state} />}
    </main>
  );
}

/**
 * Give up, start over, how to play.
 *
 * In the header rather than under the board, which is where they were: the
 * board grows all day — three history columns, then the answer sheet — so a
 * footer walks steadily further off the bottom of the screen, and "give up" is
 * needed exactly when the page has got long. Up here they are always one look
 * away and never move.
 */
function Controls({
  state,
  dispatch,
  day,
  complete,
}: {
  state: GameState;
  dispatch: (a: Action) => void;
  day?: string;
  complete: boolean;
}) {
  // Giving up cannot be taken back and survives a reload, so it asks first.
  const [confirming, setConfirming] = useState(false);
  const link =
    "underline decoration-rule underline-offset-4 hover:text-ink hover:decoration-current";

  // `!state.revealed` matters: answering the question leaves `confirming` set,
  // and without this the controls would stay stuck on a question that has
  // already been answered, with "start over" unreachable behind it.
  if (confirming && !complete && !state.revealed) {
    return (
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
        <span className="font-body text-[14px] normal-case tracking-normal text-ink">
          That closes the shelf for today and prints every way, including the
          ones you have not found.
        </span>
        <button type="button" onClick={() => dispatch({ type: "reveal" })} className={link}>
          yes, show me
        </button>
        <button type="button" onClick={() => setConfirming(false)} className={link}>
          keep playing
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
      <button
        type="button"
        onClick={() => dispatch({ type: "teach", on: true })}
        className={link}
      >
        how to play
      </button>
      {!complete && !state.revealed && (
        <button type="button" onClick={() => setConfirming(true)} className={link}>
          give up, show every way
        </button>
      )}
      {/* Anything worth wiping, not just successful moves: after giving up the
          day is over even if nothing ever reacted, and that is precisely when
          someone wants to play it again. */}
      {(state.log.length > 0 || state.failed.length > 0 || state.revealed) && (
        <button
          type="button"
          onClick={() => {
            if (day) clear(day);
            dispatch({ type: "reset" });
          }}
          className={link}
        >
          start over
        </button>
      )}
    </div>
  );
}

/**
 * The hero is the target, presented as its own reagent label.
 *
 * Showing it in the class colours it would have on the shelf is the one place
 * the whole code is stated without a legend: whatever you are making, you can
 * see what kind of thing it is before you have run a single reaction.
 */
function Header({
  bundle,
  state,
  day,
  dispatch,
}: {
  bundle: PuzzleBundle;
  state: GameState;
  day?: string;
  dispatch: (a: Action) => void;
}) {
  const record = bundle.species[bundle.target];
  const found = state.order.length;

  return (
    <header className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
        <span className="font-semibold text-brass">Quintessence</span>
        {day && <span>{day}</span>}
        <span aria-hidden>·</span>
        <span>{bundle.grade}</span>
        <span className="normal-case tracking-normal">
          — {GRADE_NOTE[bundle.grade]}
        </span>
      </div>

      {/* Not `justify-between`: on a wide screen that flung the ask 600px away
          from the compound it is asking about, and the two have to be read as
          one sentence. */}
      <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
        <div
          // Most targets are salts, and salt is deliberately the quietest
          // class — so the hero gets its presence from a lift rather than from
          // shouting with a tint the chemistry does not support.
          className={`${speciesClass(record)} species-hero flex flex-col gap-1 rounded-lg border px-5 py-4 shadow-(--shadow-lift)`}
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
            make
          </span>
          <Formula
            formula={bundle.target}
            className="species-mark font-mono text-4xl font-semibold tracking-tight sm:text-5xl"
          />
          <span className="font-display text-sm font-medium">{bundle.name}</span>
          {record && (
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
              {record.class}
            </span>
          )}
        </div>

        <div className="flex max-w-md flex-col gap-2">
          <p className="text-[17px] leading-snug">
            Find <strong className="font-display font-semibold">{bundle.want}</strong>{" "}
            different kinds of reaction that make it.
            {bundle.ways > bundle.want && (
              <>
                {" "}
                <span className="text-muted">
                  {bundle.ways} exist — every one past {bundle.want} is a bonus.
                </span>
              </>
            )}
          </p>
          <p className="font-mono text-[13px] tabular-nums text-muted">
            {/* The score turns green the moment there is a score to show, so
                the number that matters is not the same grey as the two
                counters beside it. */}
            <span className={found > 0 ? "font-semibold text-flask" : "text-ink"}>
              {found}
            </span>
            /{bundle.want} kinds
            <span className="mx-2 text-rule">|</span>
            {state.moves} {state.moves === 1 ? "move" : "moves"}
            {state.misses > 0 && (
              <>
                <span className="mx-2 text-rule">|</span>
                {state.misses} dead {state.misses === 1 ? "end" : "ends"}
              </>
            )}
          </p>

          <Controls
            state={state}
            dispatch={dispatch}
            day={day}
            complete={found >= bundle.want}
          />
        </div>
      </div>
    </header>
  );
}

function Bench({
  bundle,
  state,
  dispatch,
}: {
  bundle: PuzzleBundle;
  state: GameState;
  dispatch: (a: Action) => void;
}) {
  const [a, b] = state.selected;
  const canMix = state.selected.length === 2;
  const canHeat = state.selected.length === 1 && reactionsFor(bundle, a).length > 0;

  return (
    <section className="flex flex-col gap-4">
      <Mark>on the shelf ({state.inventory.length})</Mark>

      <div className="flex flex-wrap gap-2">
        {state.inventory.map((formula) => (
          <Chip
            key={formula}
            formula={formula}
            record={bundle.species[formula]}
            selected={state.selected.includes(formula)}
            isTarget={formula === bundle.target}
            onClick={() => dispatch({ type: "select", formula })}
          />
        ))}
      </div>

      <div className="panel flex flex-wrap items-center gap-x-4 gap-y-3 rounded-lg border p-4">
        <span className="flex items-baseline gap-2 font-mono text-[15px]">
          <Slot formula={a} bundle={bundle} placeholder="pick one" />
          <span className="text-muted">+</span>
          <Slot formula={b} bundle={bundle} placeholder="and another" />
        </span>

        <span className="ml-auto flex items-center gap-2">
          {state.selected.length > 0 && (
            <button
              type="button"
              onClick={() => dispatch({ type: "clear" })}
              className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted underline decoration-rule underline-offset-4 hover:text-ink"
            >
              clear
            </button>
          )}
          <Key onClick={() => dispatch({ type: "mix" })} disabled={!canMix} primary>
            mix
          </Key>
          <Key
            onClick={() => dispatch({ type: "decompose", formula: a })}
            disabled={!canHeat}
          >
            heat
          </Key>
        </span>
      </div>

      {state.message && (
        <p className="rounded-lg border border-rule bg-panel px-4 py-3 text-[15px] leading-snug">
          {state.message}
        </p>
      )}

      {state.last?.scored || state.last?.repeat ? <Outcome last={state.last} /> : null}
    </section>
  );
}

/**
 * The shelf after the player has given up.
 *
 * The bottles stay on the screen — they are the record of what was built, and
 * the answers below are read against them — but nothing here is a control any
 * more. The mix line is gone rather than disabled: a greyed-out button invites
 * you to work out how to un-grey it, and there is nothing to work out.
 */
function Closed({ bundle, state }: { bundle: PuzzleBundle; state: GameState }) {
  const found = state.order.length;

  return (
    <section className="flex flex-col gap-4">
      <Mark>what you had on the shelf ({state.inventory.length})</Mark>

      <div className="flex flex-wrap gap-2">
        {state.inventory.map((formula) => (
          <Chip
            key={formula}
            formula={formula}
            record={bundle.species[formula]}
            isTarget={formula === bundle.target}
          />
        ))}
      </div>

      <p className="panel rounded-lg border px-4 py-3 text-[15px] leading-snug">
        Today is done — you found{" "}
        <strong className="font-display font-semibold">{found}</strong> of{" "}
        {bundle.want} kinds in {state.moves}{" "}
        {state.moves === 1 ? "move" : "moves"}. Every way is written out below,
        yours marked. Come back tomorrow, or start over and play this one again.
      </p>
    </section>
  );
}

/** One half of the mix line: a filled label, or an empty holder. */
function Slot({
  formula,
  bundle,
  placeholder,
}: {
  formula?: string;
  bundle: PuzzleBundle;
  placeholder: string;
}) {
  if (!formula) {
    return (
      <span className="rounded border border-dashed border-rule px-2 py-1 font-body text-sm italic text-muted">
        {placeholder}
      </span>
    );
  }
  return (
    <span
      className={`${speciesClass(bundle.species[formula])} rounded border px-2 py-1`}
    >
      <Formula formula={formula} className="species-mark font-medium" />
    </span>
  );
}

/** A control on a piece of lab equipment, not a web button. */
function Key({
  children,
  onClick,
  disabled,
  primary,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={[
        "rounded border px-4 py-1.5 font-mono text-[12px] font-semibold uppercase tracking-[0.14em]",
        "transition-[transform,box-shadow,background-color] duration-100",
        "enabled:hover:-translate-y-px enabled:active:translate-y-0 disabled:opacity-35",
        primary
          ? "border-transparent bg-(--brass-solid) text-(--brass-ink) enabled:hover:bg-(--brass-lift)"
          : "border-rule bg-panel enabled:hover:border-muted",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function Outcome({ last }: { last: NonNullable<GameState["last"]> }) {
  const { reaction, scored, repeat } = last;
  return (
    <div
      key={reaction.equation}
      className={[
        "settle rounded-lg border p-4",
        scored ? "slot-filled" : "panel",
      ].join(" ")}
    >
      <Equation equation={reaction.equation} className="font-mono text-sm" />
      {reaction.note && <p className="mt-1 text-[13px] text-muted">{reaction.note}</p>}
      {scored && (
        <p className="mt-2 font-display text-sm font-semibold text-flask">
          new kind — {ruleName(reaction.rule)}
        </p>
      )}
      {repeat && (
        <p className="mt-2 text-[13px] text-muted">
          You already have this kind. It counts once, however you run it.
        </p>
      )}
    </div>
  );
}

function Picker({
  reactions,
  dispatch,
}: {
  reactions: ReactionRecord[];
  dispatch: (a: Action) => void;
}) {
  return (
    <section className="settle panel flex flex-col gap-3 rounded-lg border p-5">
      <Mark>{reactions.length} products are possible</Mark>
      <p className="max-w-prose text-[15px] leading-snug">
        One move, one product. The engine works at formula level and has no
        amounts, so it cannot know how much you added — you choose. Want the
        lot? Take them all; it costs a move each, the same as picking them one
        at a time.
      </p>
      <div className="flex flex-col gap-2">
        {reactions.map((reaction, index) => (
          <button
            key={index}
            type="button"
            onClick={() => dispatch({ type: "choose", index })}
            className="rounded-lg border border-rule bg-bench px-4 py-3 text-left transition-[transform,border-color] duration-100 hover:-translate-y-px hover:border-brass"
          >
            <Equation equation={reaction.equation} className="font-mono text-sm" />
            {reaction.note && (
              <p className="mt-1 text-[13px] text-muted">{reaction.note}</p>
            )}
          </button>
        ))}
      </div>
      {/* Below the list rather than beside it: the products are the decision,
          and a shortcut past a decision should not be the first thing read. */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Key onClick={() => dispatch({ type: "chooseAll" })}>
          take all {reactions.length} — {reactions.length} moves
        </Key>
        <button
          type="button"
          onClick={() => dispatch({ type: "cancel" })}
          className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted underline decoration-rule underline-offset-4 hover:text-ink"
        >
          change my mind — costs no move
        </button>
      </div>
    </section>
  );
}

/**
 * The rack: one slot per kind the day asks for, filled as you find them.
 *
 * Not a progress bar. The whole game is that the five have to be *different
 * kinds*, so the score has to show which kinds are in the rack — a bar of
 * anonymous green blocks says how many and hides the only part that matters.
 * Anything past `want` is a bonus and comes back in brass.
 */
function Rack({ bundle, state }: { bundle: PuzzleBundle; state: GameState }) {
  const slots = Math.max(bundle.want, state.order.length);

  return (
    <section className="flex flex-col gap-3">
      <Mark>the rack</Mark>
      <div className="grid gap-2 sm:grid-cols-2">
        {Array.from({ length: slots }).map((_, index) => {
          const rule = state.order[index];
          if (!rule) {
            return (
              <div
                key={`empty-${index}`}
                className="slot-empty min-h-13 rounded-lg border"
              />
            );
          }
          const bonus = index >= bundle.want;
          return (
            <div
              key={rule}
              className={`settle rounded-lg border px-3 py-2.5 ${bonus ? "slot-bonus" : "slot-filled"}`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-display text-[13px] font-semibold">
                  {ruleName(rule)}
                </span>
                {bonus && (
                  <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-brass">
                    bonus
                  </span>
                )}
              </div>
              <Equation
                equation={state.found[rule].equation}
                className="font-mono text-[11px] text-muted"
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}

/**
 * One margin column of history.
 *
 * Sticky and independently scrollable on a wide screen, so a long game does
 * not push the bench off the top or stretch the page to the height of whichever
 * column ran longest.
 */
function Trail({
  title,
  count,
  tone,
  className,
  children,
}: {
  title: string;
  count: number;
  tone?: "brass" | "flask" | "muted";
  className?: string;
  children: React.ReactNode[];
}) {
  return (
    <section className={`flex flex-col gap-2 ${className ?? ""}`}>
      <Mark tone={tone}>
        {title} <span className="tabular-nums">({count})</span>
      </Mark>
      <ol className="flex max-h-[60vh] flex-col gap-1.5 overflow-y-auto xl:sticky xl:top-4">
        {children.length > 0 ? (
          children
        ) : (
          <li className="px-2.5 text-[13px] italic text-muted">nothing yet</li>
        )}
      </ol>
    </section>
  );
}

/**
 * The one heading style: a mono rule, set small and wide.
 *
 * In brass by default. These sit above every section on the page, so they are
 * the cheapest place to get the accent out of the rack and onto the rest of
 * the board — and a heading is chrome, which means it can take a hue without
 * saying anything about chemistry. `tone` is for the two sections that have a
 * colour of their own already: what worked is flask green, what did not is
 * left grey, because absence should not be the brightest thing on the screen.
 */
function Mark({
  children,
  tone = "brass",
}: {
  children: React.ReactNode;
  tone?: "brass" | "flask" | "muted";
}) {
  const colour =
    tone === "flask" ? "text-flask" : tone === "muted" ? "text-muted" : "text-brass";
  return (
    <h2 className={`font-mono text-[11px] uppercase tracking-[0.16em] ${colour}`}>
      {children}
    </h2>
  );
}

function Answers({ bundle, state }: { bundle: PuzzleBundle; state: GameState }) {
  const rules = useMemo(() => Object.keys(bundle.answers), [bundle]);
  const missed = rules.filter((rule) => !(rule in state.found)).length;

  return (
    <section className="panel flex flex-col gap-4 rounded-lg border p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display text-xl font-semibold">
          Every way to make{" "}
          <Formula formula={bundle.target} className="font-mono" />
        </h2>
        <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
          {missed === 0
            ? "you found all of them"
            : `${missed} you did not find`}
        </span>
      </div>

      <ol className="flex flex-col gap-3">
        {rules.map((rule) => {
          const yours = state.found[rule];
          // Show the player's own equation where they found one: their
          // spectator ions are the version they will recognise.
          const reaction = yours ?? bundle.answers[rule];
          return (
            <li key={rule} className="flex gap-3">
              <span
                aria-hidden
                className={[
                  "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                  yours ? "bg-flask" : "bg-rule",
                ].join(" ")}
              />
              <div className="flex flex-col gap-0.5">
                <span className="font-display text-[14px] font-semibold">
                  {ruleName(rule)}
                </span>
                <Equation
                  equation={reaction.equation}
                  className="font-mono text-xs text-muted"
                />
                {reaction.note && (
                  <span className="text-[13px] text-muted">{reaction.note}</span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
