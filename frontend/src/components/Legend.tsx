"use client";

/**
 * What the colours mean.
 *
 * Collapsed by default, because the code is meant to be picked up by playing:
 * a player who mixes the red bottle with the blue one and gets a salt has
 * learned it without reading anything. This is here for the player who wants
 * it spelled out.
 */

const AXIS: [string, string][] = [
  ["acid", "turns litmus red"],
  ["acidic oxide", "becomes an acid in water"],
  ["amphoteric oxide", "acts as both — hatched both ways"],
  ["basic oxide", "becomes a base in water"],
  ["base", "turns litmus blue"],
];

const MATERIALS: [string, string][] = [
  ["salt", "an ionic lattice, so it is drawn as one"],
  ["element", "raw material, straight off the shelf"],
  ["hydride", "hydrogen with one other element"],
  ["water", "the one you get for free"],
];

export function Legend() {
  return (
    <details className="group panel rounded-lg border">
      <summary className="cursor-pointer list-none px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.14em] text-muted hover:text-ink">
        <span className="mr-1.5 inline-block transition-transform group-open:rotate-90">
          ›
        </span>
        what the colours mean
      </summary>
      <div className="grid gap-5 border-t border-rule px-4 py-4 sm:grid-cols-2">
        <Group
          title="the acid–base axis"
          note="Red one end, blue the other, exactly as litmus reads it. The oxides sit one step out: they are not an acid or a base yet, but water makes them one."
          rows={AXIS}
        />
        <Group
          title="everything else"
          note="No place on that axis, so these get a material instead of a hue."
          rows={MATERIALS}
        />
      </div>
    </details>
  );
}

function Group({
  title,
  note,
  rows,
}: {
  title: string;
  note: string;
  rows: [string, string][];
}) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
        {title}
      </h3>
      <ul className="flex flex-col gap-1.5">
        {rows.map(([name, gloss]) => (
          <li key={name} className="flex items-center gap-2.5">
            <span
              aria-hidden
              className={`species species-${name.replace(/\s+/g, "-")} h-5 w-9 shrink-0 rounded border`}
            />
            <span className="font-display text-[13px] font-medium">{name}</span>
            <span className="text-[12px] leading-tight text-muted">{gloss}</span>
          </li>
        ))}
      </ul>
      <p className="mt-1 text-[12px] leading-snug text-muted">{note}</p>
    </section>
  );
}
