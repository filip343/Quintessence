/**
 * Today's puzzle, read from disk at build time.
 *
 * The bundles in `public/puzzles` are written by `backend/chem/puzzle.py` and
 * are self-contained, so there is no API and no runtime backend: this is a
 * static page that hands one small JSON file to a client component.
 */

import { promises as fs } from "fs";
import path from "path";
import { Game } from "@/components/Game";
import type { PuzzleBundle } from "@/lib/puzzle";

const PUZZLES = path.join(process.cwd(), "public", "puzzles");

interface Index {
  version: number;
  puzzles: string[];
}

/** The most recent puzzle not in the future, so a stale build still plays. */
async function today(): Promise<{ bundle: PuzzleBundle; day: string } | null> {
  let index: Index;
  try {
    index = JSON.parse(await fs.readFile(path.join(PUZZLES, "index.json"), "utf8"));
  } catch {
    return null;
  }

  const now = new Date().toISOString().slice(0, 10);
  const available = [...index.puzzles].filter((day) => day <= now).sort();
  const day = available.at(-1) ?? [...index.puzzles].sort().at(0);
  if (!day) return null;

  const bundle: PuzzleBundle = JSON.parse(
    await fs.readFile(path.join(PUZZLES, `${day}.json`), "utf8"),
  );
  return { bundle, day };
}

export default async function Page() {
  const puzzle = await today();

  if (!puzzle) {
    return (
      <main className="mx-auto flex max-w-3xl flex-col gap-3 px-4 py-16">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
          Five Ways
        </span>
        <h1 className="font-display text-2xl font-semibold">
          The shelf is empty
        </h1>
        <p className="max-w-prose text-[15px] leading-snug">
          No puzzles have been built yet. Deal a month of them from{" "}
          <code className="rounded border border-rule bg-panel px-1.5 py-0.5 font-mono text-[13px]">
            backend/
          </code>
          :
        </p>
        <code className="w-fit rounded border border-rule bg-panel px-3 py-2 font-mono text-[13px]">
          python -m chem.puzzle --days 30
        </code>
      </main>
    );
  }

  return <Game bundle={puzzle.bundle} day={puzzle.day} />;
}
