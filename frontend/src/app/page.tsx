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
      <main className="mx-auto max-w-3xl px-4 py-16">
        <h1 className="text-xl font-semibold">No puzzles built yet</h1>
        <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          Run <code className="font-mono">python -m chem.puzzle --days 30</code> in{" "}
          <code className="font-mono">backend/</code>.
        </p>
      </main>
    );
  }

  return <Game bundle={puzzle.bundle} day={puzzle.day} />;
}
