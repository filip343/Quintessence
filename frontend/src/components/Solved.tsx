"use client";

import { useEffect, useRef } from "react";
import type { PuzzleBundle } from "@/lib/puzzle";
import { ruleName } from "@/lib/puzzle";
import { Formula } from "./Formula";

/**
 * The window that opens the moment the day is won and there is still something
 * left to find.
 *
 * Winning used to be a non-event: the answer sheet appeared under the board the
 * instant the last slot filled. That buried the win under a wall of equations
 * and — worse — printed every bonus way the player had not found yet. Bonus
 * ways are the only thing a leaderboard could ever rank, so handing them over
 * unasked is the one spoiler this game is in a position to commit.
 *
 * So the sheet waits and the player is asked. Neither answer is a trap. Keeping
 * the bench open changes nothing about the day — it is already solved, already
 * counted, already reported — and the header keeps a way to change their mind.
 * Reading the rest is the same `reveal` that giving up uses, which freezes the
 * bench, because a way copied off the sheet is not a way anybody found.
 *
 * Only opens when something is actually left. A rack already holding every way
 * there is has nothing to choose between, and the sheet may as well print.
 */
export function Solved({
  bundle,
  found,
  moves,
  left,
  onHunt,
  onReveal,
}: {
  bundle: PuzzleBundle;
  /** Rule slugs in the order they were found. */
  found: string[];
  moves: number;
  /** Ways the answer sheet would print that are not in the rack. */
  left: number;
  onHunt: () => void;
  onReveal: () => void;
}) {
  const primary = useRef<HTMLButtonElement>(null);

  // Escape keeps playing. It is the answer that throws nothing away, and an
  // overlay that reveals the answers on a stray keypress would be indefensible.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onHunt();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onHunt]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  useEffect(() => primary.current?.focus(), []);

  const bonus = found.length - bundle.want;

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center overflow-y-auto bg-[color-mix(in_oklab,var(--bench)_86%,transparent)] p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="solved-title"
    >
      <div className="panel settle flex w-full max-w-xl flex-col gap-5 rounded-xl border p-6 sm:p-8">
        <div className="flex items-baseline justify-between gap-4 font-mono text-[11px] uppercase tracking-[0.16em]">
          <span className="font-semibold text-flask">solved</span>
          <span className="tabular-nums text-muted">
            {moves} {moves === 1 ? "move" : "moves"}
          </span>
        </div>

        <div className="flex flex-col gap-4">
          <h2
            id="solved-title"
            className="font-display text-2xl font-semibold leading-tight"
          >
            You made <Formula formula={bundle.target} className="font-mono" />{" "}
            {found.length} different ways.
          </h2>

          {/* The kinds themselves, not a number. The whole game is that they
              are different, and the rack behind this window is blurred out. */}
          <ul className="flex flex-wrap gap-1.5">
            {found.map((rule, index) => (
              <li
                key={rule}
                className={[
                  "rounded border px-2 py-1 font-display text-[12px] font-medium",
                  index >= bundle.want ? "slot-bonus" : "slot-filled",
                ].join(" ")}
              >
                {ruleName(rule)}
              </li>
            ))}
          </ul>

          <p className="text-[17px] leading-relaxed">
            {bonus > 0 && (
              <>
                {bonus} of those were already past the {bundle.want} today asked
                for.{" "}
              </>
            )}
            {left === 1 ? (
              <>One more kind of reaction makes it.</>
            ) : (
              <>{left} more kinds of reaction make it.</>
            )}{" "}
            Every one is a bonus — the day is won either way, and the streak is
            already counted.
          </p>

          <p className="text-[15px] leading-snug text-muted">
            Keep the bench open and go after them, or close it and read every
            way including the {left} you have not found. The rest are still
            there to ask for later; the bench is not — printing the answers ends
            the day, the same as giving up.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-rule pt-4">
          <button
            type="button"
            onClick={onReveal}
            className="rounded border border-rule bg-panel px-4 py-1.5 font-mono text-[12px] font-semibold uppercase tracking-[0.14em] transition-[transform,border-color] duration-100 hover:-translate-y-px hover:border-muted"
          >
            show me the rest
          </button>
          <button
            ref={primary}
            type="button"
            onClick={onHunt}
            className="rounded border border-transparent bg-(--brass-solid) px-4 py-1.5 font-mono text-[12px] font-semibold uppercase tracking-[0.14em] text-(--brass-ink) transition-[transform,background-color] duration-100 hover:-translate-y-px hover:bg-(--brass-lift)"
          >
            keep hunting
          </button>
        </div>
      </div>
    </div>
  );
}
