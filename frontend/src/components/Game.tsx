"use client";

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { PuzzleBundle, ReactionRecord } from "@/lib/puzzle";
import { reactionsFor, ruleName } from "@/lib/puzzle";
import {
  type Action,
  type GameState,
  initial,
  reducer,
  replay,
  validFailures,
  won,
} from "@/lib/game";
import { clear, load, store } from "@/lib/storage";
import { Chip } from "./Chip";
import { Equation, Formula } from "./Formula";

const GRADE_STYLE: Record<string, string> = {
  easy: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  hard: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
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
    if (!save || save.moves.length === 0) return;

    const { state: rebuilt, replayed } = replay(bundle, save.moves);
    dispatch({
      type: "restore",
      state: {
        ...rebuilt,
        failed: validFailures(bundle, rebuilt, save.failed ?? []),
        revealed: save.revealed,
        restored: { kept: replayed, total: save.moves.length },
      },
    });
  }, [bundle, day]);

  useEffect(() => {
    if (!day || !hydrated.current) return;
    store(day, bundle, state.log, state.failed, state.revealed);
  }, [bundle, day, state.log, state.failed, state.revealed]);

  return (
    <main className="mx-auto flex max-w-[88rem] flex-col gap-6 px-4 py-8">
      <Header bundle={bundle} state={state} day={day} />

      {state.restored && state.restored.kept < state.restored.total && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          Restored {state.restored.kept} of {state.restored.total} saved moves — the rest
          could not be replayed against today&rsquo;s puzzle and were dropped.
        </p>
      )}

      {/*
        Three columns on a wide screen: what worked on the left, the bench in
        the middle, what did not on the right. The bench is what the eye should
        land on, so it keeps the centre and the histories fill the margins that
        were empty. Below `xl` they stack under the bench, ordered so the bench
        is still first.
      */}
      <div className="grid gap-6 xl:grid-cols-[18rem_minmax(0,1fr)_18rem] xl:items-start">
        <Trail
          title={`reactions you ran (${state.made.length})`}
          className="order-2 xl:order-1"
        >
          {[...state.made].reverse().map((reaction, index) => (
            <li
              key={`${reaction.equation}-${index}`}
              className={[
                "rounded-md border px-2.5 py-1.5",
                index === 0
                  ? "border-neutral-400 bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-900"
                  : "border-transparent",
              ].join(" ")}
            >
              <Equation
                equation={reaction.equation}
                className="font-mono text-xs text-neutral-700 dark:text-neutral-300"
              />
              {reaction.note && (
                <div className="text-[11px] text-neutral-500">{reaction.note}</div>
              )}
            </li>
          ))}
        </Trail>

        <div className="order-1 flex flex-col gap-6 xl:order-2">
          {state.pending ? (
            <Picker reactions={state.pending} dispatch={dispatch} />
          ) : (
            <Bench bundle={bundle} state={state} dispatch={dispatch} />
          )}
          <Solved state={state} />
        </div>

        <Trail
          title={`no reaction (${state.failed.length})`}
          className="order-3"
        >
          {[...state.failed].reverse().map((pair) => (
            <li
              key={pair.join("+")}
              className="rounded-md px-2.5 py-1.5 font-mono text-xs text-neutral-400 line-through decoration-neutral-300 dark:text-neutral-500 dark:decoration-neutral-700"
            >
              {pair.map((formula, index) => (
                <span key={formula}>
                  {index > 0 && <span className="mx-1 no-underline">+</span>}
                  <Formula formula={formula} />
                </span>
              ))}
            </li>
          ))}
        </Trail>
      </div>

      {(complete || state.revealed) && <Answers bundle={bundle} state={state} />}

      <div className="flex gap-4 text-xs text-neutral-500">
        {!complete && !state.revealed && (
          <button
            type="button"
            onClick={() => dispatch({ type: "reveal" })}
            className="underline underline-offset-4 hover:text-neutral-800 dark:hover:text-neutral-200"
          >
            give up and show every way
          </button>
        )}
        {state.log.length > 0 && (
          <button
            type="button"
            onClick={() => {
              if (day) clear(day);
              dispatch({ type: "reset" });
            }}
            className="underline underline-offset-4 hover:text-neutral-800 dark:hover:text-neutral-200"
          >
            start over
          </button>
        )}
      </div>
    </main>
  );
}

function Header({
  bundle,
  state,
  day,
}: {
  bundle: PuzzleBundle;
  state: GameState;
  day?: string;
}) {
  return (
    <header className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${GRADE_STYLE[bundle.grade]}`}
        >
          {bundle.grade}
        </span>
        {day && (
          <span className="text-xs text-neutral-500 dark:text-neutral-400">{day}</span>
        )}
      </div>

      <h1 className="text-3xl font-semibold tracking-tight">
        make <Formula formula={bundle.target} className="font-mono" />
      </h1>
      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        {bundle.name} — find <strong>{bundle.want}</strong> different kinds of
        reaction that produce it.
        {bundle.ways > bundle.want && ` ${bundle.ways} exist.`}
      </p>

      <div className="flex items-center gap-2">
        {Array.from({ length: bundle.want }).map((_, index) => (
          <span
            key={index}
            className={[
              "h-3 w-8 rounded-sm",
              index < state.order.length
                ? "bg-emerald-500"
                : "bg-neutral-200 dark:bg-neutral-800",
            ].join(" ")}
          />
        ))}
        <span className="ml-2 text-sm tabular-nums text-neutral-500">
          {state.order.length}/{bundle.want} · {state.moves} moves
        </span>
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
  const canHeat =
    state.selected.length === 1 && reactionsFor(bundle, a).length > 0;

  return (
    <section className="flex flex-col gap-4">
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

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900/50">
        <span className="font-mono text-sm">
          {a ? <Formula formula={a} /> : <em className="text-neutral-400">pick one</em>}
          <span className="mx-2 text-neutral-400">+</span>
          {b ? <Formula formula={b} /> : <em className="text-neutral-400">and another</em>}
        </span>

        <button
          type="button"
          disabled={!canMix}
          onClick={() => dispatch({ type: "mix" })}
          className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white enabled:hover:bg-indigo-500 disabled:opacity-40"
        >
          mix
        </button>
        <button
          type="button"
          disabled={!canHeat}
          onClick={() => dispatch({ type: "decompose", formula: a })}
          className="rounded-lg border border-neutral-300 px-4 py-1.5 text-sm enabled:hover:bg-white disabled:opacity-40 dark:border-neutral-700 dark:enabled:hover:bg-neutral-800"
        >
          heat
        </button>
        {state.selected.length > 0 && (
          <button
            type="button"
            onClick={() => dispatch({ type: "clear" })}
            className="text-xs text-neutral-500 underline underline-offset-4"
          >
            clear
          </button>
        )}
      </div>

      {state.message && (
        <p className="rounded-lg bg-neutral-100 px-4 py-3 text-sm text-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
          {state.message}
        </p>
      )}

      {state.last?.scored || state.last?.repeat ? <Outcome last={state.last} /> : null}
    </section>
  );
}

function Outcome({ last }: { last: NonNullable<GameState["last"]> }) {
  const { reaction, scored, repeat } = last;
  return (
    <div
      className={[
        "rounded-xl border p-4",
        scored
          ? "border-emerald-400 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/40"
          : "border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900",
      ].join(" ")}
    >
      <Equation equation={reaction.equation} className="font-mono text-sm" />
      {reaction.note && (
        <p className="mt-1 text-xs text-neutral-500">{reaction.note}</p>
      )}
      {scored && (
        <p className="mt-2 text-sm font-medium text-emerald-700 dark:text-emerald-400">
          new way — {ruleName(reaction.rule)}
        </p>
      )}
      {repeat && (
        <p className="mt-2 text-sm text-neutral-500">
          you already have this kind of reaction
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
    <section className="flex flex-col gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/30">
      <p className="text-sm font-medium">
        {reactions.length} products are possible — one move, one product.
      </p>
      <p className="text-xs text-neutral-600 dark:text-neutral-400">
        The engine works at formula level and has no amounts, so it cannot know
        how much you added. You choose.
      </p>
      <div className="flex flex-col gap-2">
        {reactions.map((reaction, index) => (
          <button
            key={index}
            type="button"
            onClick={() => dispatch({ type: "choose", index })}
            className="rounded-lg border border-neutral-300 bg-white px-4 py-3 text-left hover:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-900"
          >
            <Equation equation={reaction.equation} className="font-mono text-sm" />
            {reaction.note && (
              <p className="mt-1 text-xs text-neutral-500">{reaction.note}</p>
            )}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={() => dispatch({ type: "cancel" })}
        className="self-start text-xs text-neutral-500 underline underline-offset-4"
      >
        change my mind — costs no move
      </button>
    </section>
  );
}

/** The ways you have solved — green blocks, directly under the bench. */
function Solved({ state }: { state: GameState }) {
  if (state.order.length === 0) return null;
  return (
    <section className="grid gap-2 sm:grid-cols-2">
      {state.order.map((rule) => (
        <div
          key={rule}
          className="rounded-lg border border-emerald-400 bg-emerald-50 px-3 py-2 dark:border-emerald-700 dark:bg-emerald-950/40"
        >
          <div className="text-sm font-medium text-emerald-900 dark:text-emerald-200">
            {ruleName(rule)}
          </div>
          <Equation
            equation={state.found[rule].equation}
            className="font-mono text-xs text-emerald-800/80 dark:text-emerald-300/80"
          />
        </div>
      ))}
    </section>
  );
}

/**
 * Two columns: everything that reacted, and everything that did not.
 *
 * The dead ends are kept deliberately. In a 28-pair palette a player will try
 * plenty of things that do nothing, and remembering which is real progress —
 * without it they retry the same pair after a reload.
 */
/**
 * One margin column of history.
 *
 * Sticky and independently scrollable on a wide screen, so a long game does
 * not push the bench off the top or stretch the page to the height of whichever
 * column ran longest.
 */
function Trail({
  title,
  className,
  children,
}: {
  title: string;
  className?: string;
  children: React.ReactNode[];
}) {
  return (
    <section className={`flex flex-col gap-2 ${className ?? ""}`}>
      <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {title}
      </h2>
      <ol className="flex max-h-[60vh] flex-col gap-1.5 overflow-y-auto xl:sticky xl:top-4">
        {children.length > 0 ? (
          children
        ) : (
          <li className="text-xs text-neutral-400">nothing yet</li>
        )}
      </ol>
    </section>
  );
}

function Answers({ bundle, state }: { bundle: PuzzleBundle; state: GameState }) {
  const rules = useMemo(() => Object.keys(bundle.answers), [bundle]);
  const missed = rules.filter((rule) => !(rule in state.found)).length;

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-neutral-200 bg-neutral-50 p-5 dark:border-neutral-800 dark:bg-neutral-900/50">
      <h2 className="text-base font-semibold">
        every way to make <Formula formula={bundle.target} className="font-mono" />
      </h2>
      <div className="flex flex-col gap-3">
        {rules.map((rule) => {
          const yours = state.found[rule];
          // Show the player's own equation where they found one: their
          // spectator ions are the version they will recognise.
          const reaction = yours ?? bundle.answers[rule];
          return (
            <div key={rule} className="flex gap-3">
              <span
                className={[
                  "mt-1 h-2.5 w-2.5 shrink-0 rounded-full",
                  yours ? "bg-emerald-500" : "bg-neutral-300 dark:bg-neutral-700",
                ].join(" ")}
              />
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">{ruleName(rule)}</span>
                <Equation
                  equation={reaction.equation}
                  className="font-mono text-xs text-neutral-600 dark:text-neutral-400"
                />
                {reaction.note && (
                  <span className="text-xs text-neutral-500">{reaction.note}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {missed > 0 && (
        <p className="text-sm text-neutral-500">
          {missed} you did not find.
        </p>
      )}
    </section>
  );
}
