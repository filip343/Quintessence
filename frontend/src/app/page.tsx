/**
 * The front door: what day it is, how you are doing, and the way in.
 *
 * The board itself is at `/play` and is not linked from anywhere else, so
 * arriving at the game is always a decision. See `components/Home`.
 */

import { Empty } from "@/components/Empty";
import { Home } from "@/components/Home";
import { puzzleDays } from "@/lib/manifest";

export default async function Page() {
  const available = await puzzleDays();
  if (available.length === 0) return <Empty />;
  return <Home days={available} />;
}
