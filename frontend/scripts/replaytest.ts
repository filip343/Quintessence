/**
 * Prove that a saved game cannot smuggle anything into a puzzle.
 *
 * The honest case: a real game's log replays to exactly the same state.
 * The dishonest cases: every way of editing a save by hand is truncated at the
 * bad move, so nothing enters the inventory that the bundle did not produce.
 *
 *   npx tsx scripts/replaytest.ts
 */

import { promises as fs } from "fs";
import path from "path";
import type { PuzzleBundle } from "../src/lib/puzzle";
import {
  type GameState,
  type Move,
  initial,
  reducer,
  replay,
  validFailures,
} from "../src/lib/game";
import { reactionsFor } from "../src/lib/puzzle";

const PUZZLES = path.join(process.cwd(), "public", "puzzles");

let failures = 0;

function check(name: string, ok: boolean, detail = "") {
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  -- ${detail}` : ""}`);
}

/** Play a genuine game so we have a real log to attack. */
function honestGame(bundle: PuzzleBundle): GameState {
  let state = initial(bundle);
  const have = new Set(bundle.palette);

  for (let round = 0; round < 6; round++) {
    for (const reaction of bundle.reactions) {
      if (reaction.substrates.some((s) => !have.has(s) || s === bundle.target)) continue;
      if (reaction.products.every((p) => have.has(p))) continue;

      const [a, b] = reaction.substrates;
      let next =
        b === undefined
          ? reducer(bundle, state, { type: "decompose", formula: a })
          : reducer(
              bundle,
              reducer(bundle, reducer(bundle, state, { type: "select", formula: a }), {
                type: "select",
                formula: b,
              }),
              { type: "mix" },
            );
      if (next.pending) {
        const index = next.pending.findIndex((r) => r.equation === reaction.equation);
        next = reducer(bundle, next, { type: "choose", index: index < 0 ? 0 : index });
      }
      if (next.log.length > state.log.length) {
        state = next;
        reaction.products.forEach((p) => have.add(p));
      }
    }
  }
  return state;
}

/** A pair the player holds that genuinely does nothing. */
function findDeadEnd(bundle: PuzzleBundle, inventory: string[]): string[] | null {
  for (const a of inventory) {
    for (const b of inventory) {
      if (a >= b || a === bundle.target || b === bundle.target) continue;
      if (reactionsFor(bundle, a, b).length === 0) return [a, b].sort();
    }
  }
  return null;
}

async function main() {
  const file = (await fs.readdir(PUZZLES))
    .filter((f) => f.endsWith(".json") && f !== "index.json")
    .sort()[0];
  const bundle: PuzzleBundle = JSON.parse(
    await fs.readFile(path.join(PUZZLES, file), "utf8"),
  );
  console.log(`replay integrity, ${bundle.target} (${file})\n`);

  const honest = honestGame(bundle);
  console.log(`  a real game: ${honest.log.length} moves, ${honest.order.length} ways\n`);

  // 1. An untouched log rebuilds the game exactly.
  const clean = replay(bundle, honest.log);
  check(
    "honest log replays intact",
    clean.replayed === honest.log.length &&
      clean.state.inventory.length === honest.inventory.length &&
      clean.state.order.length === honest.order.length,
    `${clean.replayed}/${honest.log.length} moves`,
  );

  // 2. A species that is not in the puzzle at all.
  const injected: Move[] = [
    { substrates: ["PuO2", "H2O"], equation: "PuO2 + H2O -> PuO2(OH)2" },
  ];
  check(
    "invented species rejected",
    replay(bundle, injected).replayed === 0 &&
      !replay(bundle, injected).state.inventory.includes("PuO2"),
  );

  // 3. A real reaction from the bundle, but fired before its inputs exist.
  const late = honest.log.find((m) => !bundle.palette.includes(m.substrates[0]));
  if (late) {
    check(
      "move fired before its inputs exist is rejected",
      replay(bundle, [late]).replayed === 0,
      late.equation,
    );
  }

  // 4. Real substrates, but a product the bundle never offers for that pair.
  const first = honest.log[0];
  const forged: Move[] = [{ substrates: first.substrates, equation: `${first.substrates.join(" + ")} -> ${bundle.target}` }];
  check(
    "forged equation for a real pair is rejected",
    replay(bundle, forged).replayed === 0 &&
      !replay(bundle, forged).state.found[bundle.target],
  );

  // 5. A valid prefix followed by a bad move keeps the prefix, drops the rest.
  const tampered: Move[] = [...honest.log.slice(0, 2), injected[0], ...honest.log.slice(2)];
  const partial = replay(bundle, tampered);
  check(
    "tampered log truncates at the bad move",
    partial.replayed === 2 && partial.replayed < tampered.length,
    `kept ${partial.replayed}/${tampered.length}`,
  );

  // 6. Nothing a replay produces is outside the bundle's own species list.
  const known = new Set(Object.keys(bundle.species));
  const strays = clean.state.inventory.filter((f) => !known.has(f));
  check("replayed inventory stays inside the bundle", strays.length === 0, strays.join(", "));

  // 7. The target cannot be used as a reagent even from a save.
  const circular: Move[] = [
    { substrates: [bundle.target, bundle.palette[0]], equation: "anything" },
  ];
  check("target refused as a reagent on replay", replay(bundle, circular).replayed === 0);

  // 8. The two history columns get the data they render.
  check(
    "every applied move lands in `made`",
    clean.state.made.length === clean.state.log.length && clean.state.made.length > 0,
    `${clean.state.made.length} reactions`,
  );

  const dead = findDeadEnd(bundle, clean.state.inventory);
  if (dead) {
    const [x, y] = dead;
    let s = reducer(bundle, clean.state, { type: "select", formula: x });
    s = reducer(bundle, s, { type: "select", formula: y });
    s = reducer(bundle, s, { type: "mix" });
    const once = s.failed.length;
    s = reducer(bundle, s, { type: "select", formula: x });
    s = reducer(bundle, s, { type: "select", formula: y });
    s = reducer(bundle, s, { type: "mix" });
    check(
      "a dead end is recorded once, not twice",
      once === clean.state.failed.length + 1 && s.failed.length === once,
      `${dead.join(" + ")}`,
    );
  }

  // 9. Saved dead ends are re-checked, not trusted.
  const deadEnd = findDeadEnd(bundle, clean.state.inventory);
  const claimedFailures = [
    ...(deadEnd ? [deadEnd] : []), // genuine
    ["PuO2", "H2O"], // species that do not exist here
    honest.log[0].substrates, // a pair that really does react
    [bundle.target, bundle.palette[0]], // the target again
    ...(deadEnd ? [[...deadEnd].reverse()] : []), // the same pair, reversed
  ];
  const kept = validFailures(bundle, clean.state, claimedFailures);
  check(
    "saved dead ends re-checked on load",
    kept.length === (deadEnd ? 1 : 0),
    `kept ${kept.length} of ${claimedFailures.length} claimed`,
  );

  console.log(`\n${failures === 0 ? "all checks passed" : `${failures} FAILED`}`);
  process.exit(failures === 0 ? 0 : 1);
}

void main();
