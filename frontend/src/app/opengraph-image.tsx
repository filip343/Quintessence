/**
 * The link preview.
 *
 * Generated rather than drawn, so it cannot drift from the palette: the colours
 * here are the dark bench, the brass and the flask green the game itself uses.
 * Deliberately evergreen — it shows the rack, not today's compound. A preview
 * built from the day's target would be stale the moment the next puzzle lands,
 * and every share of the link would spoil a target for whoever clicked it.
 *
 * Satori, which renders this, is not a browser: it takes inline styles only,
 * wants `display: flex` stated on anything with more than one child, and knows
 * nothing about Tailwind or the stylesheet. Hence the long-hand.
 */

import { ImageResponse } from "next/og";

export const alt =
  "Quintessence - a daily chemistry puzzle. Find five different kinds of reaction that make the day's compound.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const BENCH = "#0f1317";
const PANEL = "#161b21";
const INK = "#e7ecf0";
const MUTED = "#8d99a4";
const RULE = "#262e36";
const BRASS = "#c9a24a";
const FLASK = "#3fbf9e";

/** One slot on the rack: found, or still open. */
function Slot({ label, filled }: { label: string; filled: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        width: 196,
        height: 62,
        paddingLeft: 18,
        borderRadius: 10,
        border: `1px solid ${filled ? "rgba(63, 191, 158, 0.45)" : RULE}`,
        background: filled ? "rgba(63, 191, 158, 0.12)" : "transparent",
        color: filled ? FLASK : MUTED,
        fontSize: 19,
        letterSpacing: filled ? 0 : 2,
      }}
    >
      {label}
    </div>
  );
}

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          width: "100%",
          height: "100%",
          padding: 68,
          background: BENCH,
          color: INK,
          // Satori has no stylesheet to inherit from, so the base font is
          // stated once here and everything below rides on it.
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              display: "flex",
              color: MUTED,
              fontSize: 22,
              letterSpacing: 7,
              textTransform: "uppercase",
            }}
          >
            a daily chemistry puzzle
          </div>
          <div
            style={{
              display: "flex",
              marginTop: 18,
              fontSize: 104,
              fontWeight: 700,
              letterSpacing: -2,
            }}
          >
            Quintessence
          </div>
          <div
            style={{
              display: "flex",
              marginTop: 22,
              maxWidth: 760,
              color: MUTED,
              fontSize: 31,
              lineHeight: 1.4,
            }}
          >
            One compound. Five different kinds of reaction that make it.
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
          <div style={{ display: "flex", gap: 14 }}>
            <Slot label="neutralisation" filled />
            <Slot label="displacement" filled />
            <Slot label="precipitation" filled />
            <Slot label="? ? ?" filled={false} />
            <Slot label="? ? ?" filled={false} />
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              paddingTop: 26,
              borderTop: `1px solid ${RULE}`,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                padding: "10px 20px",
                borderRadius: 8,
                border: `1px solid ${RULE}`,
                background: PANEL,
                color: INK,
                fontSize: 26,
                fontFamily: "monospace",
              }}
            >
              2 K + I₂ → 2 KI
            </div>
            <div style={{ display: "flex", color: BRASS, fontSize: 24 }}>
              real, balanced, no textbook needed
            </div>
          </div>
        </div>
      </div>
    ),
    size,
  );
}
