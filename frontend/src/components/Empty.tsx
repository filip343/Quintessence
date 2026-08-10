/**
 * No puzzles have been built. Shown by both routes, because either one can be
 * the first thing a developer opens after cloning.
 */
export function Empty() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-3 px-4 py-16">
      <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
        Quintessence
      </span>
      <h1 className="font-display text-2xl font-semibold">The shelf is empty</h1>
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
