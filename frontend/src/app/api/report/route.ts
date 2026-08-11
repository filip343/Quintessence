/**
 * Where a report goes.
 *
 * This is the first server function in a site that is otherwise entirely
 * static, so it is worth being exact about what it does and does not change:
 * the *chemistry* still never runs on a server. A dealt hand is still a JSON
 * bundle the browser plays offline, and the end screen still works when the
 * network does not. This endpoint carries one thing in the other direction — a
 * sentence somebody typed — and when it is down, or not configured, the game
 * plays exactly as it did before it existed.
 *
 * Resend's REST API rather than its SDK: the call is one POST with a bearer
 * token, and a dependency added to build that object is a dependency to keep
 * audited. `RESEND_FROM` is optional because Resend's shared `onboarding@
 * resend.dev` sender can only deliver to the account's own address, which is
 * precisely where these are going; a verified domain is only needed the day
 * they should come from somewhere else.
 *
 * A public endpoint that sends mail is a thing strangers will find, so the
 * shape of the input is checked before any of it is used, and the mail is
 * `text` with no `html` field — a report is a stranger's prose, and plain text
 * has no markup to inject into.
 */

import {
  CONTACT_LIMIT,
  CONTEXT_LIMIT,
  KINDS,
  KIND_LABELS,
  MESSAGE_LIMIT,
  type Kind,
} from "@/lib/report";

/** Refused before parsing. The largest legitimate report is far under this. */
const BODY_LIMIT = 32_000;

const WINDOW_MS = 60_000;
const PER_WINDOW = 5;

/**
 * A serverless instance is not a server: this map is per-instance and dies with
 * it, so it bounds a burst from one client rather than enforcing a global
 * quota, and saying otherwise would be pretending. It costs nothing and stops
 * the accident that actually happens — a retry loop in a left-open tab — while
 * the real ceiling is Resend's own quota.
 */
const recent = new Map<string, number[]>();

function limited(who: string): boolean {
  const now = Date.now();
  const hits = (recent.get(who) ?? []).filter((at) => now - at < WINDOW_MS);
  hits.push(now);
  recent.set(who, hits);
  // Unbounded otherwise: every distinct address would keep an entry for the
  // life of the instance.
  if (recent.size > 500) {
    for (const [key, times] of recent) {
      if (times.every((at) => now - at >= WINDOW_MS)) recent.delete(key);
    }
  }
  return hits.length > PER_WINDOW;
}

/** Tab, newline and return. A report is prose and its paragraphs are part of it. */
const KEEP = new Set([9, 10, 13]);

/**
 * Trimmed, capped, and stripped of control characters -- which in a field like
 * this are only ever an attempt to smuggle structure into something that will be
 * rendered as text. Compared by code point rather than matched by a regex full of
 * escapes, because the escapes are the part that gets read wrong later.
 */
function text(value: unknown, limit: number): string {
  if (typeof value !== "string") return "";
  let out = "";
  for (const character of value) {
    const code = character.codePointAt(0) ?? 0;
    if ((code < 32 || code === 127) && !KEEP.has(code)) continue;
    out += character;
  }
  return out.trim().slice(0, limit);
}

/** One line, for a subject. Newlines are what makes a subject two headers. */
function line(value: string, limit: number): string {
  return value.replace(/[\r\n]+/g, " ").slice(0, limit);
}

/**
 * Deliberately loose. This decides whether to set `reply_to`, and the cost of
 * being wrong either way is small — a rejected address someone wanted, against
 * a bounce. Anything stricter rejects real addresses for no gain.
 */
function isAddress(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export async function POST(request: Request): Promise<Response> {
  const key = process.env.RESEND_API_KEY;
  const to = process.env.REPORT_TO;
  if (!key || !to) {
    // Not an error on the caller's part, and the dialog says so rather than
    // blaming the report. Loud in the log because it is a deployment mistake.
    console.warn("report: RESEND_API_KEY or REPORT_TO is not set");
    return Response.json({ error: "unconfigured" }, { status: 503 });
  }

  if (!request.headers.get("content-type")?.includes("application/json")) {
    return Response.json({ error: "expected json" }, { status: 415 });
  }
  const declared = Number(request.headers.get("content-length") ?? 0);
  if (declared > BODY_LIMIT) {
    return Response.json({ error: "too long" }, { status: 413 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "expected json" }, { status: 400 });
  }
  if (typeof body !== "object" || body === null) {
    return Response.json({ error: "expected json" }, { status: 400 });
  }
  const fields = body as Record<string, unknown>;

  // The client never sends this field, so anything in it filled a form field
  // it could not see. Answered with a success it will not check, because a bot
  // told it failed is a bot that tries again.
  if (text(fields.website, 100)) {
    return Response.json({ ok: true });
  }

  const message = text(fields.message, MESSAGE_LIMIT);
  if (!message) {
    return Response.json({ error: "empty" }, { status: 400 });
  }

  const kind: Kind = KINDS.includes(fields.kind as Kind)
    ? (fields.kind as Kind)
    : "bug";
  const contact = text(fields.contact, CONTACT_LIMIT);
  const context = text(fields.context, CONTEXT_LIMIT);

  const who =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (limited(who)) {
    return Response.json({ error: "slow down" }, { status: 429 });
  }

  // The first line of the report is the subject, so a glance at the inbox says
  // what it is about. `line` matters here and not merely for tidiness.
  const subject = line(
    `[quintessence] ${KIND_LABELS[kind]} — ${message.split("\n")[0]}`,
    120,
  );

  const sent = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: process.env.REPORT_FROM ?? "Quintessence <onboarding@resend.dev>",
      to: [to],
      subject,
      // `reply_to` only when it could work. An address that cannot be replied
      // to is worse than none, because it looks like one that can.
      ...(isAddress(contact) ? { reply_to: contact } : {}),
      text: [
        message,
        "",
        "--",
        KIND_LABELS[kind],
        contact ? `from ${contact}` : "no contact given",
        "",
        context || "no context attached",
      ].join("\n"),
    }),
  }).catch(() => null);

  if (!sent?.ok) {
    // The body may carry a reason worth having — an unverified domain, a bad
    // key — and it is the kind of thing that is only ever read once, in a log,
    // when reports stop arriving.
    console.error("report: resend refused", sent?.status, await sent?.text());
    return Response.json({ error: "not sent" }, { status: 502 });
  }

  return Response.json({ ok: true });
}
