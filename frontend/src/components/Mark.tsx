/**
 * The one heading style: a mono rule, set small and wide.
 *
 * In brass by default. These sit above every section on both pages, so they are
 * the cheapest place to get the accent out of the rack and onto the rest of the
 * board — and a heading is chrome, which means it can take a hue without saying
 * anything about chemistry. `tone` is for the two sections that have a colour of
 * their own already: what worked is flask green, what did not is left grey,
 * because absence should not be the brightest thing on the screen.
 */
export function Mark({
  children,
  tone = "brass",
}: {
  children: React.ReactNode;
  tone?: "brass" | "flask" | "muted";
}) {
  const colour =
    tone === "flask" ? "text-flask" : tone === "muted" ? "text-muted" : "text-brass";
  return (
    <h2 className={`font-mono text-[11px] uppercase tracking-[0.16em] ${colour}`}>
      {children}
    </h2>
  );
}
