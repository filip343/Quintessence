/**
 * The board.
 *
 * Its own route rather than the home page's second half, so that finishing a
 * day and coming back to it are different places — and so the bench is not what
 * loads when someone types the bare domain in on a morning they have already
 * played.
 *
 * Which day this is remains a browser decision; this route only hands over the
 * list of days that exist. See `Today`.
 */

import type { Metadata } from "next";
import { Empty } from "@/components/Empty";
import { Today } from "@/components/Today";
import { puzzleDays } from "@/lib/manifest";

export const metadata: Metadata = {
  title: "Today's puzzle - Quintessence",
};

export default async function Page() {
  const available = await puzzleDays();
  if (available.length === 0) return <Empty />;
  return <Today days={available} />;
}
