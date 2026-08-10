/**
 * The list of days that exist, read from disk at build time.
 *
 * Only the list. *Which* of them is today is decided in the browser -- see
 * `lib/day` and the note in `Today` for why reading the clock on the server was
 * a bug that froze the site on whatever day it was last built.
 *
 * The list is safe to bake in because the bundles are committed alongside it:
 * whatever `index.json` said at build time is exactly the set of files the
 * deployment serves, so there is nothing for a runtime read to discover. That
 * keeps every route static with no API and no runtime backend, which is the
 * whole premise -- the browser is handed a manifest and fetches one small
 * self-contained JSON file.
 *
 * Server-side only: it touches `fs`, so it may be imported by a page but never
 * by anything marked `"use client"`.
 */

import { promises as fs } from "fs";
import path from "path";

const PUZZLES = path.join(process.cwd(), "public", "puzzles");

interface Index {
  version: number;
  puzzles: string[];
}

export async function puzzleDays(): Promise<string[]> {
  try {
    const index: Index = JSON.parse(
      await fs.readFile(path.join(PUZZLES, "index.json"), "utf8"),
    );
    return index.puzzles;
  } catch {
    return [];
  }
}
