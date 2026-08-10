"use client";

/**
 * Which day is it, decided in the browser.
 *
 * This used to be a build-time decision, and that was a bug with a long fuse.
 * `page.tsx` read the clock inside a server component; nothing in that reads
 * `cookies()` or `headers()`, so Next saw no reason not to prerender it, and
 * `new Date()` is invisible to that analysis in a way those functions are not.
 * The page went out as static HTML with one day's puzzle baked in, and stayed
 * on that day until something else forced a rebuild. `next dev` re-runs server
 * components per request, so the whole class of fault was invisible locally.
 *
 * Rebuilding daily would paper over it. It would not fix it: puzzles are dealt
 * weekly, so between runs nothing pushes, nothing rebuilds, and the site parks
 * itself on whichever day it was last deployed. Reading the clock on the
 * machine that has the clock is the actual fix, and it costs one fetch of a
 * file the CDN is already serving.
 *
 * **UTC, not local time.** Everyone gets the same compound at the same instant,
 * which is what lets two people compare a score without first agreeing on whose
 * midnight counts. `page.tsx` always meant this -- it used `toISOString()` --
 * and this only moves where it is evaluated, not what it decides.
 *
 * The picking itself lives in `lib/day`, because the home page has to reach the
 * same answer and a countdown that disagrees with the board about which day it
 * is would be worse than no countdown.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { pick, utcToday } from "@/lib/day";
import type { PuzzleBundle } from "@/lib/puzzle";
import { Game } from "./Game";

export function Today({ days }: { days: string[] }) {
  const [puzzle, setPuzzle] = useState<{ day: string; bundle: PuzzleBundle } | null>(
    null,
  );
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const day = pick(days, utcToday());
    if (!day) {
      setFailed(true);
      return;
    }

    // Not re-checked on focus or on a timer. A tab left open across midnight
    // keeps the day it started, because swapping the board out from under
    // somebody mid-game to award them a puzzle they did not ask for is worse
    // than being a day stale until they reload.
    let alive = true;
    fetch(`/puzzles/${day}.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json();
      })
      .then((bundle: PuzzleBundle) => alive && setPuzzle({ day, bundle }))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [days]);

  if (failed) {
    return (
      <Shell>
        <h1 className="font-display text-2xl font-semibold">
          Today&rsquo;s puzzle would not load
        </h1>
        <p className="max-w-prose text-[15px] leading-snug text-muted">
          The bench is set but the reagents never arrived. Reloading usually
          does it.
        </p>
        <Link
          href="/"
          className="w-fit font-mono text-[11px] uppercase tracking-[0.12em] text-muted underline decoration-rule underline-offset-4 hover:text-ink"
        >
          back to the front
        </Link>
      </Shell>
    );
  }

  if (!puzzle) {
    // Deliberately not a copy of the board. A skeleton that mimics the real
    // layout invites you to start reading a hand that is not there yet.
    return (
      <Shell>
        <p className="text-[15px] leading-snug text-muted" role="status">
          Setting out today&rsquo;s bench&hellip;
        </p>
      </Shell>
    );
  }

  return <Game bundle={puzzle.bundle} day={puzzle.day} />;
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-352 flex-col gap-3 px-4 py-8 sm:px-6">
      <Link
        href="/"
        className="w-fit font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-brass hover:underline hover:decoration-current hover:underline-offset-4"
      >
        Quintessence
      </Link>
      {children}
    </main>
  );
}
