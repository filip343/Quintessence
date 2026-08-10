"use client";

/**
 * The front door.
 *
 * Everything true across days lives here — the compound, the run you are on,
 * how long until the next one — and the board is one door away at `/play`.
 * Splitting them is what gives a daily its shape: a game you finish and come
 * back to needs somewhere to come back *to*, and landing straight on a finished
 * board says only "you already did this".
 *
 * The layout is asymmetric on purpose: the compound reads left as a headline,
 * the specimen sits right as a label lifted off the bench, and the run is a
 * divided strip along the bottom rather than a row of boxes. A centred stack of
 * three identical tiles is the shape every generated page takes, and it says
 * nothing about a chemistry set.
 *
 * Nothing here can be rendered on the server. The clock, the save and the run
 * are all read from the browser, and prerendering any of them would commit the
 * HTML to a countdown that was already wrong when it was built — the fault
 * `Today` documents, in a form that would be visible rather than silent. So the
 * masthead and the door are static and everything else arrives after mount,
 * against skeletons cut to the size of what replaces them.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { after, countdown, pick, until, utcToday } from "@/lib/day";
import { replay, won } from "@/lib/game";
import type { PuzzleBundle } from "@/lib/puzzle";
import { speciesClass } from "@/lib/puzzle";
import {
  currentStreak,
  load,
  readResults,
  readStreak,
  type Result,
} from "@/lib/storage";
import { cn } from "@/lib/utils";
import { Formula } from "./Formula";
import { Glassware } from "./Glassware";
import { Badge } from "./ui/badge";
import { buttonVariants } from "./ui/button";
import { Separator } from "./ui/separator";
import { Skeleton } from "./ui/skeleton";

/** Where today stands, worked out from the save the way the board works it out. */
interface Standing {
  ways: number;
  moves: number;
  solved: boolean;
  revealed: boolean;
  /** Whether anything has happened yet — a move, or giving up. */
  started: boolean;
}

interface Front {
  /** The day being served, which is today unless the calendar has run out. */
  day: string;
  late: boolean;
  /** `null` when the bundle would not load; the page still works, with less to say. */
  bundle: PuzzleBundle | null;
  standing: Standing | null;
  next?: string;
}

interface Stats {
  streak: number;
  best: number;
  played: number;
  solved: number;
  ways: number;
}

export function Home({ days }: { days: string[] }) {
  const [front, setFront] = useState<Front | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [now, setNow] = useState(0);

  useEffect(() => {
    const today = utcToday();
    const day = pick(days, today);
    if (!day) return;

    let alive = true;

    // One landing for both outcomes, and every piece of browser state read in
    // the same tick: the clock the countdown starts from has to be the clock
    // the day was chosen against, or the two can straddle a midnight.
    const land = (bundle: PuzzleBundle | null) => {
      if (!alive) return;
      setFront({
        day,
        late: day !== today,
        bundle,
        standing: bundle ? standing(day, bundle) : null,
        next: after(days, day),
      });
      setStats(read(today));
      setNow(Date.now());
    };

    fetch(`/puzzles/${day}.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json();
      })
      .then((bundle: PuzzleBundle) => land(bundle))
      .catch(() => land(null));

    return () => {
      alive = false;
    };
  }, [days]);

  // Started only once there is something to count towards, so a page that never
  // resolves never ticks.
  useEffect(() => {
    if (!front) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [front]);

  return (
    <main className="mx-auto flex min-h-[100dvh] w-full max-w-[1400px] flex-col gap-14 px-4 py-10 sm:px-8 sm:py-14">
      {/* Mono rather than the display face, and widely tracked: it reads as the
          plate on a piece of equipment, and stays clearly a *wordmark* next to
          the compound name below, which is the one thing on the page allowed to
          be big and typographic. */}
      <header className="flex flex-col gap-1.5">
        <span className="font-mono text-xl font-semibold uppercase tracking-[0.3em] text-brass sm:text-2xl">
          Quintessence
        </span>
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
          a daily chemistry puzzle
        </span>
      </header>

      <Day front={front} now={now} />

      {/* Never a skeleton and never conditional: the bench is the room, not the
          content, and a room that arrives late is a room that flickers. It also
          does the work the hero used to do by stretching — the page reaches the
          fold because there is something down here, rather than because a
          section was told to absorb whatever was left over. */}
      <div className="settle" style={rise(4)}>
        <Glassware />
      </div>

      <Footing stats={stats} />
    </main>
  );
}

/**
 * The day: what to make on the left, what it looks like on the right.
 *
 * The compound is named here rather than held back until the board. The puzzle
 * is the routes, not the identity of the target — the board prints it the
 * instant you arrive — so keeping it back bought nothing and cost the page the
 * one image it has.
 */
function Day({ front, now }: { front: Front | null; now: number }) {
  const bundle = front?.bundle ?? null;
  const standing = front?.standing ?? null;
  const done = standing?.solved || standing?.revealed;

  return (
    <section
      className="grid items-center gap-12 lg:grid-cols-12 lg:gap-16"
      aria-busy={!front}
    >
      <div className="flex flex-col gap-7 lg:col-span-7 lg:pr-8">
        <div className="settle flex flex-wrap items-center gap-x-3 gap-y-2" style={rise(0)}>
          {front ? (
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
              {/* "Today" would be a lie once the calendar has run out and `pick`
                  has fallen back to the newest day it has. */}
              {front.late ? "latest" : "today"} — {longDate(front.day)}
            </span>
          ) : (
            <Skeleton className="h-4 w-52" />
          )}
          {bundle && (
            <Badge
              variant="outline"
              className="h-5 rounded-full border-rule px-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-brass"
            >
              {bundle.grade}
            </Badge>
          )}
        </div>

        <h1
          // Names arrive lowercase from the bundle, which is right in an
          // equation and wrong as a headline.
          className="settle font-display text-4xl font-semibold leading-none tracking-tighter text-balance first-letter:uppercase md:text-6xl"
          style={rise(1)}
        >
          {front ? (
            bundle ? (
              bundle.name
            ) : (
              "Today’s compound"
            )
          ) : (
            <>
              <span className="sr-only">Looking up today’s compound</span>
              <span className="flex flex-col gap-3" aria-hidden>
                <Skeleton className="h-10 w-full max-w-lg md:h-14" />
                <Skeleton className="h-10 w-2/3 max-w-sm md:h-14" />
              </span>
            </>
          )}
        </h1>

        {front ? (
          <p
            className="settle max-w-[46ch] text-[17px] leading-relaxed text-muted"
            style={rise(2)}
          >
            {describe(bundle, standing)}
          </p>
        ) : (
          <Skeleton className="h-5 w-full max-w-md" />
        )}

        {standing?.started && bundle && !done && (
          <Progress ways={standing.ways} want={bundle.want} />
        )}

        {/* The door is never a skeleton. Where it goes was never a question the
            browser had to answer — only what to call it was — so it is in the
            served HTML, gets prefetched on sight, and works before any script
            does. */}
        <div
          className="settle flex flex-wrap items-center gap-x-6 gap-y-4"
          style={rise(3)}
        >
          {/* The styling from `Button`, but a real anchor. Base UI's Button
              expects a native <button> and says so loudly when handed a link —
              rightly, since the two differ in keyboard behaviour, middle-click
              and what a screen reader announces. This is navigation, so the
              variants are borrowed and the element stays an <a>. `cn` and not
              cva's own merge: the size class has to *replace* the default
              height rather than sit next to it and win on stylesheet order. */}
          <Link
            href="/play"
            className={cn(
              buttonVariants(),
              "h-12 rounded-lg px-6 font-mono text-[12px] font-semibold uppercase tracking-[0.16em] shadow-(--shadow-lift) hover:-translate-y-px",
            )}
          >
            {!standing?.started ? "open the bench" : done ? "look again" : "carry on"}
          </Link>
          {front && <Countdown day={front.next} now={now} />}
        </div>
      </div>

      <div className="lg:col-span-5">
        {front ? (
          <Specimen bundle={bundle} />
        ) : (
          <Skeleton className="h-56 w-full max-w-70 rounded-xl" />
        )}
      </div>
    </section>
  );
}

/**
 * The target, drawn as the reagent label it is on the board — the class tint
 * and texture say what kind of substance it is before a word is read.
 *
 * Two elements, not one: `settle` and `drift` both animate `transform`, and the
 * second would cancel the first if they shared a node.
 */
function Specimen({ bundle }: { bundle: PuzzleBundle | null }) {
  if (!bundle) {
    return (
      <div className="settle rounded-xl border border-dashed border-rule p-7" style={rise(2)}>
        <p className="text-[15px] leading-snug text-muted">
          Today&rsquo;s bundle would not load from here. The bench will have
          more to say.
        </p>
      </div>
    );
  }

  const record = bundle.species[bundle.target];

  return (
    <div className="settle" style={rise(2)}>
      <div
        className={`${speciesClass(record)} species-hero drift flex w-fit flex-col gap-2.5 rounded-xl border px-9 py-8 shadow-(--shadow-lift)`}
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted">
          make
        </span>
        <Formula
          formula={bundle.target}
          className="species-mark font-mono text-6xl font-semibold tracking-tight md:text-7xl"
        />
        {record && (
          <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
            {record.class}
          </span>
        )}
      </div>
    </div>
  );
}

/** The rack, shrunk to a strip: which of the day's slots are filled. */
function Progress({ ways, want }: { ways: number; want: number }) {
  const slots = Math.max(want, ways);

  return (
    <div className="settle flex flex-col gap-2.5" style={rise(3)}>
      <div className="flex flex-wrap gap-1.5" aria-hidden>
        {Array.from({ length: slots }).map((_, index) => (
          <span
            key={index}
            className={`h-2.5 w-10 rounded-[3px] border ${
              index >= ways
                ? "slot-empty"
                : index >= want
                  ? "slot-bonus"
                  : "slot-filled"
            }`}
          />
        ))}
      </div>
      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
        {ways} of {want} kinds found
      </span>
    </div>
  );
}

function describe(bundle: PuzzleBundle | null, standing: Standing | null) {
  if (!bundle) {
    return "Mix two things, keep what they make, and find five different kinds of reaction that produce the day’s compound.";
  }
  if (standing?.solved) {
    return (
      <>
        Solved — <Strong tone="flask">{standing.ways}</Strong>{" "}
        {standing.ways === 1 ? "kind" : "kinds"} in {standing.moves}{" "}
        {standing.moves === 1 ? "move" : "moves"}. The full write-up is on the
        board.
      </>
    );
  }
  if (standing?.revealed) {
    return (
      <>
        Closed out with {standing.ways} of {bundle.want} kinds. Every way is
        written up on the board, yours marked.
      </>
    );
  }
  return (
    <>
      Find <Strong>{bundle.want}</Strong> different kinds of reaction that make
      it.
      {bundle.ways > bundle.want && (
        <> {bundle.ways} exist — everything past {bundle.want} is a bonus.</>
      )}
    </>
  );
}

function Strong({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone?: "flask";
}) {
  return (
    <strong
      className={`font-display font-semibold ${tone === "flask" ? "text-flask" : "text-ink"}`}
    >
      {children}
    </strong>
  );
}

function Countdown({ day, now }: { day?: string; now: number }) {
  const style = "font-mono text-[11px] uppercase tracking-[0.14em] text-muted";

  // No next day on the calendar. Saying nothing would read as a bug; a
  // countdown to a midnight that brings nothing would be worse.
  if (!day) {
    return <span className={style}>no puzzle scheduled after this one yet</span>;
  }

  const left = until(day, now);
  if (left <= 0) {
    return <span className={style}>a new puzzle is ready — reload</span>;
  }

  return (
    <span className={`flex items-center gap-2 ${style}`}>
      <span className="size-1.5 animate-pulse rounded-full bg-brass" aria-hidden />
      next in <span className="tabular-nums text-ink">{countdown(left)}</span>
    </span>
  );
}

/**
 * The run, along the bottom.
 *
 * A divided strip rather than a row of cards: three boxed tiles is the house
 * style of every generated dashboard, and a box earns its border by lifting
 * something off the page. These numbers are not lifted off anything — they are
 * a footnote to the day above, and a rule plus space says so.
 */
function Footing({ stats }: { stats: Stats | null }) {
  return (
    <section className="flex flex-col gap-8">
      <Separator className="bg-rule" />

      {stats === null ? (
        <StripSkeleton />
      ) : stats.played > 0 || stats.streak > 0 ? (
        <Strip>
          <Stat
            index={0}
            value={stats.streak}
            label={stats.streak === 1 ? "day in a row" : "days in a row"}
            note={stats.best > 0 ? `best run ${stats.best}` : undefined}
            lit={stats.streak > 0}
          />
          <Stat
            index={1}
            value={stats.solved}
            label={stats.solved === 1 ? "day solved" : "days solved"}
            note={`of ${stats.played} finished`}
          />
          <Stat
            index={2}
            value={stats.ways}
            label={stats.ways === 1 ? "kind found" : "kinds found"}
            note="bonus ways counted"
          />
        </Strip>
      ) : (
        // Nothing played yet. Three zeroes is a worse welcome than no numbers,
        // and someone with an empty bench is exactly who has not been told the
        // rules — so the strip carries the rules instead, in the same shape.
        <Strip>
          {STEPS.map(([title, body], index) => (
            <Step key={title} index={index} title={title} body={body} />
          ))}
        </Strip>
      )}
    </section>
  );
}

/** One shape, used for the run and for the rules. */
function Strip({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid gap-8 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-rule">
      {children}
    </div>
  );
}

function Cell({
  index,
  children,
}: {
  index: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className="settle flex flex-col gap-1.5 sm:px-8 sm:first:pl-0 sm:last:pr-0"
      style={rise(4 + index)}
    >
      {children}
    </div>
  );
}

function Stat({
  index,
  value,
  label,
  note,
  lit,
}: {
  index: number;
  value: number;
  label: string;
  note?: string;
  lit?: boolean;
}) {
  return (
    <Cell index={index}>
      <span
        className={`font-mono text-4xl font-semibold leading-none tabular-nums ${lit ? "text-flask" : "text-ink"}`}
      >
        {value}
      </span>
      <span className="font-mono text-[11px] uppercase tracking-[0.16em]">
        {label}
      </span>
      {note && <span className="text-[13px] text-muted">{note}</span>}
    </Cell>
  );
}

const STEPS: [string, string][] = [
  ["Mix", "Put two things from the shelf together and see what comes out."],
  ["Keep", "Whatever they make joins the shelf. Nothing is ever used up."],
  ["Win", "Five different kinds of reaction that make the target take the day."],
];

function Step({
  index,
  title,
  body,
}: {
  index: number;
  title: string;
  body: string;
}) {
  return (
    <Cell index={index}>
      <span className="font-mono text-[11px] font-semibold tabular-nums text-brass">
        {String(index + 1).padStart(2, "0")}
      </span>
      <span className="font-display text-base font-semibold">{title}</span>
      <span className="text-[15px] leading-snug text-muted">{body}</span>
    </Cell>
  );
}

/** Cut to the size of what replaces it, so the strip does not jump. */
function StripSkeleton() {
  return (
    <Strip>
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className="flex flex-col gap-2 sm:px-8 sm:first:pl-0 sm:last:pr-0"
          aria-hidden
        >
          <Skeleton className="h-9 w-16" />
          <Skeleton className="h-3 w-28" />
        </div>
      ))}
    </Strip>
  );
}

/** The staggered reveal, as a cascade rather than a timeline. */
function rise(index: number): React.CSSProperties {
  return { animationDelay: `${index * 70}ms` };
}

/** Fixed locale: the game is UTC and ISO everywhere, and so is this. */
function longDate(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

/**
 * Where today stands, from the save alone.
 *
 * Replayed through the reducer rather than read off the save, because the save
 * holds only a move log — deliberately, so that nothing derived from it is ever
 * trusted. That makes this the same computation the board does on load, which
 * is the point: the two screens cannot disagree about how far you got.
 */
function standing(day: string, bundle: PuzzleBundle): Standing {
  const save = load(day, bundle);
  if (!save) {
    return { ways: 0, moves: 0, solved: false, revealed: false, started: false };
  }
  const { state } = replay(bundle, save.moves);
  return {
    ways: state.order.length,
    moves: state.moves,
    solved: won(state, bundle),
    revealed: save.revealed,
    // A day whose whole story is "I gave up" has an empty log and has still
    // been started.
    started: save.moves.length > 0 || save.revealed,
  };
}

function read(today: string): Stats {
  const results: Result[] = Object.values(readResults());
  const streak = readStreak();
  return {
    streak: currentStreak(streak, today),
    best: streak?.best ?? 0,
    played: results.length,
    solved: results.filter((result) => result.solved).length,
    ways: results.reduce((total, result) => total + result.ways, 0),
  };
}
