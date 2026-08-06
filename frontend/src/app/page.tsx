/**
 * The list of days that exist, read from disk at build time.
 *
 * Only the list. *Which* of them is today is decided in the browser, by
 * `Today` -- see the note there for why reading the clock here was a bug that
 * froze the site on whatever day it was last built.
 *
 * The list is safe to bake in because the bundles are committed alongside it:
 * whatever `index.json` said at build time is exactly the set of files the
 * deployment serves, so there is nothing for a runtime read to discover. That
 * keeps this a static page with no API and no runtime backend, which is the
 * whole premise -- the browser is handed a manifest and fetches one small
 * self-contained JSON file.
 */

import { promises as fs } from "fs";
import path from "path";
import { Today } from "@/components/Today";

const PUZZLES = path.join(process.cwd(), "public", "puzzles");

interface Index {
  version: number;
  puzzles: string[];
}

async function days(): Promise<string[]> {
  try {
    const index: Index = JSON.parse(
      await fs.readFile(path.join(PUZZLES, "index.json"), "utf8"),
    );
    return index.puzzles;
  } catch {
    return [];
  }
}

export default async function Page() {
  const available = await days();

  if (available.length === 0) {
    return (
      <main className="mx-auto flex max-w-3xl flex-col gap-3 px-4 py-16">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
          Quintessence
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

  return <Today days={available} />;
}
