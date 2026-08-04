/**
 * Play every built puzzle to completion through the real reducer.
 *
 * Not a unit test of the chemistry -- the backend already proves every reaction
 * balances. This proves the *game* is winnable as shipped: that the bundle the
 * front end loads actually contains the ways it advertises, and that the
 * reducer's rules (one move one product, the target refused as a reagent) do
 * not accidentally make a day impossible.
 *
 *   npx tsx scripts/playtest.ts
 */

import { promises as fs } from "fs";
import path from "path";
import type { PuzzleBundle, ReactionRecord } from "../src/lib/puzzle";
import { type GameState, initial, reducer, won } from "../src/lib/game";

const PUZZLES = path.join(process.cwd(), "public", "puzzles");

/** Cheapest-first search for a reaction sequence that builds `formula`. */
function buildOrder(bundle: PuzzleBundle, want: string[]): ReactionRecord[] {
  const have = new Set(bundle.palette);
  const steps: ReactionRecord[] = [];
  const targets = [...want];

  // Repeatedly fire anything whose substrates are all in hand, until the
  // wanted species appear. Breadth-first over the closure; it is tiny.
  for (let round = 0; round < 12 && targets.some((t) => !have.has(t)); round++) {
    for (const reaction of bundle.reactions) {
      if (reaction.products.includes(bundle.target)) continue; // scored separately
      if (reaction.substrates.some((s) => !have.has(s) || s === bundle.target)) continue;
      if (reaction.products.every((p) => have.has(p))) continue;
      steps.push(reaction);
      reaction.products.forEach((p) => have.add(p));
    }
  }
  return steps;
}

async function play(file: string): Promise<string> {
  const bundle: PuzzleBundle = JSON.parse(
    await fs.readFile(path.join(PUZZLES, file), "utf8"),
  );
  const step = (s: GameState, a: Parameters<typeof reducer>[2]) =>
    reducer(bundle, s, a);

  let state = initial(bundle);

  // Build out the closure, then fire one reaction per advertised way.
  for (const reaction of buildOrder(bundle, Object.values(bundle.answers).flatMap((r) => r.substrates))) {
    state = fire(state, reaction, step);
  }
  for (const reaction of Object.values(bundle.answers)) {
    if (reaction.substrates.every((s) => state.inventory.includes(s))) {
      state = fire(state, reaction, step);
    }
  }

  const ok = won(state, bundle);
  return [
    ok ? "PASS" : "FAIL",
    file.replace(".json", "").padEnd(12),
    bundle.target.padEnd(12),
    `${state.order.length}/${bundle.want} ways`,
    `${state.moves} moves`,
    ok ? "" : `-- missing ${Object.keys(bundle.answers).filter((r) => !(r in state.found)).join(", ")}`,
  ].join("  ");
}

function fire(
  state: GameState,
  reaction: ReactionRecord,
  step: (s: GameState, a: Parameters<typeof reducer>[2]) => GameState,
): GameState {
  const [a, b] = reaction.substrates;
  let next =
    b === undefined
      ? step(state, { type: "decompose", formula: a })
      : step(step(step(state, { type: "clear" }), { type: "select", formula: a }), {
          type: "select",
          formula: b,
        });
  if (b !== undefined) next = step(next, { type: "mix" });

  // A multi-product mix pauses for a choice; take the one we came for.
  if (next.pending) {
    const index = next.pending.findIndex(
      (option) => option.equation === reaction.equation,
    );
    next = step(next, { type: "choose", index: index >= 0 ? index : 0 });
  }
  return next;
}

async function main() {
  const files = (await fs.readdir(PUZZLES))
    .filter((f) => f.endsWith(".json") && f !== "index.json")
    .sort();

  const results = await Promise.all(files.map(play));
  results.forEach((line) => console.log(line));

  const failed = results.filter((line) => line.startsWith("FAIL")).length;
  console.log(`\n${results.length - failed}/${results.length} puzzles winnable`);
  process.exit(failed === 0 ? 0 : 1);
}

void main();
