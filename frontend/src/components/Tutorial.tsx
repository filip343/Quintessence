"use client";

import { useEffect, useRef, useState } from "react";
import type { PuzzleBundle } from "@/lib/puzzle";
import { ruleName } from "@/lib/puzzle";
import { Equation, Formula } from "./Formula";

/**
 * How to play, shown once.
 *
 * Five cards rather than one wall of prose: the rules of this game are each one
 * sentence long, and the two that actually surprise people — that a kind counts
 * once however you run it, and that the target cannot be an ingredient — get
 * lost in a paragraph. Read at your own pace, skippable at any point, and
 * reachable again from the header afterwards.
 */

interface Step {
  title: string;
  body: React.ReactNode;
  figure?: React.ReactNode;
}

/**
 * A rack slot, drawn as the player will meet it.
 *
 * Deliberately the same green fill and the same rule name the rack uses, so the
 * card is not an illustration of the scoring but a picture of it — two
 * equations sharing one block says "one slot" better than a sentence does.
 */
function Slot({
  rule,
  equations,
  caption,
}: {
  rule: string;
  equations: string[];
  caption: string;
}) {
  return (
    <div className="slot-filled flex flex-col gap-1 rounded-lg border px-3 py-2.5">
      <span className="font-display text-[13px] font-semibold">{ruleName(rule)}</span>
      {equations.map((equation) => (
        <Equation key={equation} equation={equation} className="font-mono text-[15px]" />
      ))}
      <span className="text-[13px] italic text-muted">{caption}</span>
    </div>
  );
}

/** Bottles as they appear on the shelf, for the colour card. */
function Swatch({ name, label }: { name: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span
        aria-hidden
        className={`species species-${name} h-5 w-8 shrink-0 rounded border`}
      />
      <span className="text-[13px] text-muted">{label}</span>
    </span>
  );
}

function steps(bundle: PuzzleBundle): Step[] {
  return [
    {
      // The ask is not always five: a hard target has few ways precisely
      // because it is hard, so the day scales down rather than being excluded.
      // The title has to move with it or it contradicts the sentence under it.
      title: `${bundle.want} ways to make one thing`,
      body: (
        <>
          Every day there is one compound to build — today it is{" "}
          <Formula formula={bundle.target} className="font-mono font-medium" />,{" "}
          {bundle.name}. Your job is to find{" "}
          <strong className="font-display font-semibold">{bundle.want}</strong>{" "}
          different <em>kinds</em> of reaction that produce it.
        </>
      ),
    },
    {
      title: "Pick two, and mix",
      body: (
        <>
          Click two bottles on the shelf and press <Key>mix</Key>. A few things
          come apart on their own — pick one and press <Key>heat</Key>. Whatever
          the reaction makes joins your shelf, and nothing is ever used up, so
          you can build an intermediate once and reuse it all day.
        </>
      ),
    },
    {
      title: "Kinds, not routes",
      body: (
        <>
          This is the part that catches people out. Swapping a spectator ion
          does not make a new kind of reaction — driving a weak acid out of its
          salt is one kind whether you reach for the iron or the zinc. Change
          the <em>chemistry</em> and you have a second kind.
        </>
      ),
      figure: (
        <div className="flex flex-col gap-2">
          <Slot
            rule="acid_displacement"
            equations={["FeS + 2 HCl -> H2S + FeCl2", "ZnS + 2 HCl -> H2S + ZnCl2"]}
            caption="two routes, one slot"
          />
          <Slot
            rule="hydrogenation"
            equations={["H2 + S -> H2S"]}
            caption="different chemistry, so a slot of its own"
          />
        </div>
      ),
    },
    {
      title: "Nothing here can go wrong",
      body: (
        <>
          There is no move limit, no timer and no way to lose. A pair that does
          nothing is written down so you never have to try it twice. The single
          thing you cannot do is use the target itself as an ingredient —
          consuming it to make it is not a way to make it.
        </>
      ),
    },
    {
      title: "The bottles are colour-coded",
      body: (
        <>
          Colour places a substance on the acid&ndash;base scale you already
          know from litmus, and the pattern says what it is — a lattice for
          ionic solids, mirrored hatching for acids and bases. You never need
          it, but it is faster than reading every label. The full key sits under
          the bench.
        </>
      ),
      figure: (
        <div className="grid grid-cols-2 gap-x-5 gap-y-1.5 sm:grid-cols-3">
          <Swatch name="acid" label="acid" />
          <Swatch name="base" label="base" />
          <Swatch name="salt" label="salt" />
          <Swatch name="element" label="element" />
          <Swatch name="acidic-oxide" label="acidic oxide" />
          <Swatch name="basic-oxide" label="basic oxide" />
        </div>
      ),
    },
  ];
}

/** A key on the bench, inline in a sentence. */
function Key({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded border border-rule bg-bench px-1.5 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em]">
      {children}
    </span>
  );
}

export function Tutorial({
  bundle,
  onClose,
}: {
  bundle: PuzzleBundle;
  onClose: () => void;
}) {
  const cards = steps(bundle);
  const [index, setIndex] = useState(0);
  const last = index === cards.length - 1;
  const primary = useRef<HTMLButtonElement>(null);

  // Escape skips, and the arrows page. Bound to the document rather than to the
  // dialog so it works before anything inside has been focused.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowRight")
        setIndex((current) => Math.min(current + 1, cards.length - 1));
      if (event.key === "ArrowLeft") setIndex((current) => Math.max(current - 1, 0));
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [cards.length, onClose]);

  // The board behind is a full page of its own; letting it scroll under the
  // card is the kind of thing that makes an overlay feel broken.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  useEffect(() => {
    primary.current?.focus();
  }, [index]);

  const card = cards[index];

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center overflow-y-auto bg-[color-mix(in_oklab,var(--bench)_86%,transparent)] p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tutorial-title"
    >
      <div className="panel settle flex w-full max-w-xl flex-col gap-5 rounded-xl border p-6 sm:p-8">
        <div className="flex items-baseline justify-between gap-4 font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
          <span>how to play</span>
          <span className="tabular-nums">
            {index + 1} / {cards.length}
          </span>
        </div>

        <div className="flex min-h-45 flex-col gap-4">
          <h2
            id="tutorial-title"
            className="font-display text-2xl font-semibold leading-tight"
          >
            {card.title}
          </h2>
          <p className="text-[17px] leading-relaxed">{card.body}</p>
          {card.figure}
        </div>

        <div className="flex flex-wrap items-center gap-3 border-t border-rule pt-4">
          {/* Dots, not a bar: five is few enough to count, and they say how
              much is left without pretending to be a loading indicator. */}
          <div className="flex items-center gap-1.5" aria-hidden>
            {cards.map((step, dot) => (
              <span
                key={step.title}
                className={[
                  "h-1.5 rounded-full transition-[width,background-color] duration-200",
                  dot === index ? "w-5 bg-brass" : "w-1.5 bg-rule",
                ].join(" ")}
              />
            ))}
          </div>

          <div className="ml-auto flex items-center gap-2">
            {!last && (
              <button
                type="button"
                onClick={onClose}
                className="px-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted underline decoration-rule underline-offset-4 hover:text-ink"
              >
                skip
              </button>
            )}
            <button
              type="button"
              onClick={() => setIndex((current) => Math.max(current - 1, 0))}
              disabled={index === 0}
              className="rounded border border-rule bg-panel px-4 py-1.5 font-mono text-[12px] font-semibold uppercase tracking-[0.14em] transition-[transform,border-color] duration-100 enabled:hover:-translate-y-px enabled:hover:border-muted disabled:opacity-35"
            >
              back
            </button>
            <button
              ref={primary}
              type="button"
              onClick={() =>
                last ? onClose() : setIndex((current) => current + 1)
              }
              className="rounded border border-transparent bg-(--brass-solid) px-4 py-1.5 font-mono text-[12px] font-semibold uppercase tracking-[0.14em] text-(--brass-ink) transition-[transform,background-color] duration-100 hover:-translate-y-px hover:bg-(--brass-lift)"
            >
              {last ? "start playing" : "next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
