/**
 * A shelf of reagents, drawn rather than photographed.
 *
 * Decoration, but not arbitrary decoration: every bottle is filled with one of
 * the class tints from `globals.css` — acid red, base blue, salt kraft, the
 * blue-green of water — so the shelf is quietly the same colour code the board
 * teaches, met before it has to be read. It is `aria-hidden` throughout; there
 * is nothing here a screen reader would want.
 *
 * The glass takes its fill and edge from the theme variables, so it inverts
 * with everything else and no dark case is written twice. The pieces rock on
 * their bases rather than bobbing up and down — bottles standing on a shelf do
 * not float — each on its own period, so the row never pulses in unison.
 */

import { cn } from "@/lib/utils";

/** Theme-aware glass. Barely there in light, barely there in dark. */
const GLASS = "color-mix(in oklab, var(--ink) 5%, transparent)";
const SHEEN = "color-mix(in oklab, var(--panel) 70%, transparent)";
const EDGE = "var(--rule)";
const LIQUID = "color-mix(in oklab, var(--tint) 60%, transparent)";
const CAP = "color-mix(in oklab, var(--tint) 40%, var(--rule))";

type Kind = "bottle" | "flask" | "beaker" | "round" | "tube";

interface Piece {
  kind: Kind;
  /** One of the species tints. */
  tint: string;
  /** Tailwind height; the width follows the viewBox. */
  size: string;
  /** Seconds. Deliberately coprime-ish so the row never syncs up. */
  period: number;
  delay: number;
  tilt: number;
  /** Mirrored, so a repeated shape does not read as a repeated shape. */
  flip?: boolean;
}

/**
 * Nine pieces, and no two neighbours the same shape, height or colour — a row
 * of identical bottles reads as a pattern swatch rather than as a shelf that
 * someone actually works at. The tints are the class colours: acid red, base
 * blue, salt kraft, acidic-oxide amber, the blue-green of water.
 */
/**
 * Three groups, spread across the plank rather than nine pieces at even
 * centres — glassware in use ends up in clusters, and an evenly spaced row is
 * the one arrangement that reads as clip art instead of as a shelf.
 *
 * A shelf is one row or it is not a shelf, so a narrow screen drops whole
 * groups from the right rather than wrapping them onto a second plank.
 */
const CLUSTERS: { show?: string; pieces: Piece[] }[] = [
  {
    pieces: [
      { kind: "flask", tint: "#1b4f9c", size: "h-32 sm:h-40", period: 19, delay: -11, tilt: 1 },
      { kind: "tube", tint: "#1d8fa8", size: "h-22 sm:h-26", period: 13, delay: -2, tilt: 0 },
      { kind: "bottle", tint: "#b3261e", size: "h-28 sm:h-36", period: 17, delay: -7, tilt: -1 },
    ],
  },
  {
    show: "hidden sm:flex",
    pieces: [
      { kind: "beaker", tint: "#b0761a", size: "h-22 sm:h-28", period: 15, delay: -6, tilt: 0 },
      // Teal rather than the salt kraft it started as: kraft at 60% over a cool
      // bench goes muddy, and on the one piece with no label to break it up
      // that is the whole object.
      { kind: "round", tint: "#17766b", size: "h-28 sm:h-34", period: 11, delay: -4, tilt: 0 },
      { kind: "bottle", tint: "#7a6e5d", size: "h-24 sm:h-30", period: 23, delay: -14, tilt: 1, flip: true },
    ],
  },
  {
    show: "hidden lg:flex",
    pieces: [
      { kind: "flask", tint: "#b0761a", size: "h-28 sm:h-34", period: 21, delay: -9, tilt: -1, flip: true },
      { kind: "tube", tint: "#6a4fbe", size: "h-20 sm:h-24", period: 14, delay: -5, tilt: 0 },
      { kind: "beaker", tint: "#1d8fa8", size: "h-26 sm:h-32", period: 18, delay: -3, tilt: 0, flip: true },
    ],
  },
];

export function Glassware({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("flex w-full flex-col", className)}>
      <div className="flex w-full items-end justify-between gap-4">
        {CLUSTERS.map((cluster, index) => (
          <div
            key={index}
            className={cn("flex items-end gap-1 sm:gap-2", cluster.show)}
          >
            {cluster.pieces.map((piece, at) => (
              <Vessel key={`${piece.kind}-${at}`} {...piece} />
            ))}
          </div>
        ))}
      </div>
      {/* The plank. A shadow rather than a border, so the bottles read as
          standing on it instead of being boxed by it. */}
      <div className="h-1.5 rounded-[2px] bg-rule shadow-(--shadow-lift)" />
    </div>
  );
}

function Vessel({ kind, tint, size, period, delay, tilt, flip }: Piece) {
  const shapes = SHAPES[kind];

  return (
    <svg
      viewBox={VIEWBOX[kind]}
      className={cn(size, "sway w-auto shrink-0")}
      style={
        {
          "--tint": tint,
          "--sway-period": `${period}s`,
          // Negative, so every piece is already mid-swing on the first frame
          // instead of the whole row starting from rest together.
          "--sway-delay": `${delay}s`,
          "--tilt": `${tilt}deg`,
        } as React.CSSProperties
      }
    >
      {/* Mirrored inside the SVG rather than with a `scale-x` utility: the
          animation owns `transform` on this element and would drop it. */}
      {flip ? (
        <g transform={`translate(${WIDTH[kind]} 0) scale(-1 1)`}>{shapes}</g>
      ) : (
        shapes
      )}
    </svg>
  );
}

const VIEWBOX: Record<Kind, string> = {
  bottle: "0 0 48 122",
  flask: "0 0 60 122",
  beaker: "0 0 56 122",
  round: "0 0 60 122",
  tube: "0 0 26 122",
};

/** The viewBox widths, which is what a mirror has to translate back by. */
const WIDTH: Record<Kind, number> = {
  bottle: 48,
  flask: 60,
  beaker: 56,
  round: 60,
  tube: 26,
};

/** One stroke width across the set, per the house rule for icons. */
const STROKE = 1.5;

const SHAPES: Record<Kind, React.ReactNode> = {
  bottle: (
    <>
      <rect x="16" y="4" width="16" height="11" rx="2.5" fill={CAP} />
      <rect x="18.5" y="14" width="11" height="6" rx="1" fill={EDGE} />
      <path
        d="M20 20h8v11c0 5 10 9 10 21v60c0 5-4 8-9 8H19c-5 0-9-3-9-8V52c0-12 10-16 10-21V20z"
        fill={GLASS}
        stroke={EDGE}
        strokeWidth={STROKE}
      />
      <path
        d="M10 66h28v46c0 5-4 8-9 8H19c-5 0-9-3-9-8V66z"
        fill={LIQUID}
      />
      <rect x="13" y="74" width="22" height="24" rx="2" fill={SHEEN} />
      <rect x="14.5" y="56" width="3" height="26" rx="1.5" fill={SHEEN} />
    </>
  ),
  flask: (
    <>
      <rect x="23" y="15" width="14" height="5" rx="2" fill={EDGE} />
      <path
        d="M25 20h10v26l17 58c1.5 5-2 10-7 10H15c-5 0-8.5-5-7-10l17-58V20z"
        fill={GLASS}
        stroke={EDGE}
        strokeWidth={STROKE}
      />
      <path
        d="M19.5 86h21l4.5 12c1.5 5-2 10-7 10H22c-5 0-8.5-5-7-10l4.5-12z"
        fill={LIQUID}
      />
      <rect x="26.5" y="26" width="2.5" height="18" rx="1.25" fill={SHEEN} />
    </>
  ),
  beaker: (
    <>
      <path
        d="M11 30h34v76c0 5-4 8-9 8H20c-5 0-9-3-9-8V30z"
        fill={GLASS}
        stroke={EDGE}
        strokeWidth={STROKE}
      />
      <path
        d="M11 62h34v44c0 5-4 8-9 8H20c-5 0-9-3-9-8V62z"
        fill={LIQUID}
      />
      {/* Graduations, which is what makes it a beaker and not a cup. */}
      {[42, 52, 74, 88].map((y) => (
        <rect key={y} x="34" y={y} width="8" height="1.5" rx="0.75" fill={EDGE} />
      ))}
      <rect x="15" y="38" width="3" height="20" rx="1.5" fill={SHEEN} />
    </>
  ),
  round: (
    <>
      <rect x="24" y="15" width="12" height="5" rx="2" fill={EDGE} />
      <path
        d="M25 20h10v24h-10z"
        fill={GLASS}
        stroke={EDGE}
        strokeWidth={STROKE}
      />
      <circle
        cx="30"
        cy="84"
        r="27"
        fill={GLASS}
        stroke={EDGE}
        strokeWidth={STROKE}
      />
      {/* Chord at y=88, so the flask is a little over half full. */}
      <path d="M3.3 88a27 27 0 0 0 53.4 0z" fill={LIQUID} />
      {/* An arc, not a dot: a round highlight on a round body reads as a hole
          punched through it rather than as light on glass. */}
      <path
        d="M12 76a19 19 0 0 1 10-16"
        fill="none"
        stroke={SHEEN}
        strokeWidth="3.5"
        strokeLinecap="round"
      />
    </>
  ),
  tube: (
    <>
      <rect x="3.5" y="19" width="19" height="5" rx="2" fill={EDGE} />
      <path
        d="M6 24h14v78c0 6-3 10-7 10s-7-4-7-10V24z"
        fill={GLASS}
        stroke={EDGE}
        strokeWidth={STROKE}
      />
      <path
        d="M6 66h14v36c0 6-3 10-7 10s-7-4-7-10V66z"
        fill={LIQUID}
      />
      <rect x="8.5" y="32" width="2.5" height="22" rx="1.25" fill={SHEEN} />
    </>
  ),
};
