/**
 * Formulas with real subscripts: `Li2CO3` renders as Li₂CO₃.
 *
 * Splitting on digits is enough because a species formula never carries a
 * charge — the engine writes `Ca(OH)2`, not `Ca+2`. Charges only appear on
 * ions, which the player never handles directly.
 */

interface Props {
  formula: string;
  className?: string;
}

export function Formula({ formula, className }: Props) {
  const parts = formula.split(/(\d+)/).filter(Boolean);
  return (
    <span className={className}>
      {parts.map((part, index) =>
        /^\d+$/.test(part) ? (
          <sub key={index} className="text-[0.7em]">
            {part}
          </sub>
        ) : (
          <span key={index}>{part}</span>
        ),
      )}
    </span>
  );
}

/** A whole balanced equation: `2 LiOH + CO2 -> Li2CO3 + H2O`. */
export function Equation({
  equation,
  className,
}: {
  equation: string;
  className?: string;
}) {
  return (
    <span className={className}>
      {equation.split(/\s+/).map((token, index) => {
        if (token === "->") {
          return (
            <span key={index} className="mx-1.5 text-neutral-400">
              →
            </span>
          );
        }
        if (token === "+") {
          return (
            <span key={index} className="mx-1 text-neutral-400">
              +
            </span>
          );
        }
        // A bare leading number is a coefficient, not a subscript.
        if (/^\d+$/.test(token)) {
          return (
            <span key={index} className="mr-0.5 text-neutral-500">
              {token}
            </span>
          );
        }
        return <Formula key={index} formula={token} />;
      })}
    </span>
  );
}
