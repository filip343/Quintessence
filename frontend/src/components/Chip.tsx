"use client";

import type { SpeciesRecord } from "@/lib/puzzle";
import { STATE_NAMES, speciesClass } from "@/lib/puzzle";
import { Formula } from "./Formula";

interface Props {
  formula: string;
  record?: SpeciesRecord;
  selected?: boolean;
  isTarget?: boolean;
  onClick?: () => void;
}

/**
 * One bottle on the shelf.
 *
 * The class carries the colour and the texture; state is written the way it is
 * written in an equation, `NaCl(s)`, rather than as a coloured badge — a second
 * colour code on the same object would fight the first, and the parenthesised
 * form is what the player will meet in a textbook anyway.
 *
 * With no `onClick` it is a label rather than a button: once the day is over
 * the shelf is a record, so it drops out of the tab order and stops lifting
 * under the cursor. It keeps its full colour — it is not disabled, it is done.
 */
export function Chip({ formula, record, selected, isTarget, onClick }: Props) {
  const interactive = Boolean(onClick);

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      title={
        record
          ? `${record.name} — ${record.class}, ${STATE_NAMES[record.state]}`
          : formula
      }
      aria-pressed={selected}
      className={[
        speciesClass(record),
        "group relative flex min-w-[7.5rem] flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left",
        interactive
          ? "transition-[transform,box-shadow] duration-150 hover:-translate-y-px hover:shadow-(--shadow-lift)"
          : "cursor-default",
        selected
          ? "ring-2 ring-(--brass-lift) ring-offset-2 ring-offset-bench -translate-y-px shadow-(--shadow-lift)"
          : "",
        isTarget ? "opacity-45 saturate-50" : "",
      ].join(" ")}
    >
      <span className="flex items-baseline">
        <Formula
          formula={formula}
          className="species-mark font-mono text-[15px] font-medium tracking-tight"
        />
        {record && (
          <span className="species-mark ml-0.5 self-end pb-px text-[10px] opacity-70">
            ({record.state})
          </span>
        )}
      </span>
      <span className="max-w-[16ch] truncate text-[11px] leading-tight text-muted">
        {isTarget ? "what you are making" : (record?.name ?? "")}
      </span>
    </button>
  );
}
