"use client";

import type { SpeciesRecord } from "@/lib/puzzle";
import { STATE_NAMES } from "@/lib/puzzle";
import { Formula } from "./Formula";

const STATE_STYLES: Record<SpeciesRecord["state"], string> = {
  s: "text-amber-700 dark:text-amber-500",
  l: "text-sky-700 dark:text-sky-400",
  g: "text-emerald-700 dark:text-emerald-400",
  aq: "text-indigo-700 dark:text-indigo-400",
};

interface Props {
  formula: string;
  record?: SpeciesRecord;
  selected?: boolean;
  isTarget?: boolean;
  onClick?: () => void;
}

export function Chip({ formula, record, selected, isTarget, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={
        record ? `${record.name} — ${STATE_NAMES[record.state]}` : formula
      }
      aria-pressed={selected}
      className={[
        "group flex flex-col items-start rounded-lg border px-3 py-2 text-left transition",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
        selected
          ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-400 dark:bg-indigo-950/60"
          : "border-neutral-200 bg-white hover:border-neutral-400 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-neutral-600",
        isTarget ? "opacity-60" : "",
      ].join(" ")}
    >
      <span className="flex items-baseline gap-1.5">
        <Formula
          formula={formula}
          className="font-mono text-base font-medium text-neutral-900 dark:text-neutral-100"
        />
        {record && (
          <span className={`text-[10px] font-semibold ${STATE_STYLES[record.state]}`}>
            {record.state}
          </span>
        )}
      </span>
      <span className="max-w-[14ch] truncate text-[11px] text-neutral-500 dark:text-neutral-400">
        {isTarget ? "your answer" : (record?.name ?? "")}
      </span>
    </button>
  );
}
