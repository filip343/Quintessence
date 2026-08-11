"use client";

/**
 * Say something is wrong, from inside the game.
 *
 * A mailto: would have cost nothing to build and would have been reported
 * through roughly never — it asks someone to leave the page, open a client
 * that on a phone may not exist, invent a subject line, and address a stranger,
 * all to say "this looked wrong". The whole point of a report button is that
 * the report is cheap at the moment of noticing, and everything in that list is
 * a place to give up.
 *
 * What the box actually buys, though, is the attachment. The page knows the
 * day, the target, the bundle and every move that has been made; a player knows
 * "the copper one". `report.attachment` assembles the first into something
 * reproducible, and the panel shows it in full before anything is sent, because
 * attaching somebody's move log to their message without showing them is not a
 * thing to do quietly.
 *
 * It docks in the corner from the root layout, so it is on every page including
 * the ones that are a page precisely because something went wrong. That is also
 * why it does not take the subject as props — see `report.publish`.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import {
  KINDS,
  KIND_LABELS,
  MESSAGE_LIMIT,
  attachment,
  current,
  submit,
  type Kind,
  type Outcome,
  type Subject,
} from "@/lib/report";

type Status = "idle" | "sending" | Outcome;

export function Report() {
  const [subject, setSubject] = useState<Subject | null>(null);

  return (
    <>
      {/* Bottom right: the theme toggle already owns the top corner, and a
          report button at the top of a page reads as part of the masthead
          rather than as something to reach for when a reaction looks wrong. */}
      <button
        type="button"
        onClick={() => setSubject(current())}
        className="panel fixed right-4 bottom-4 z-40 rounded-md border px-4 py-2 font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-muted transition-[color,transform] duration-150 hover:-translate-y-px hover:text-ink"
      >
        report a problem
      </button>
      {/* Out to the body rather than rendered in place. Fixed positioning is
          relative to the nearest transformed ancestor rather than to the
          viewport, so a dialog that trusts its mount point is one `transform`
          away from being laid out inside whatever opened it — and the panel
          would otherwise inherit the `font-mono uppercase` chrome around the
          button, which turned the sentence explaining the attachment into
          shouted monospace. */}
      {subject !== null &&
        createPortal(
          <Panel subject={subject} onClose={() => setSubject(null)} />,
          document.body,
        )}
    </>
  );
}

function Panel({
  subject,
  onClose,
}: {
  subject: Subject;
  onClose: () => void;
}) {
  const [kind, setKind] = useState<Kind>("chemistry");
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [showing, setShowing] = useState(false);
  const box = useRef<HTMLTextAreaElement>(null);

  // Frozen at the moment the panel opens — `subject` was snapshotted by the
  // button. Reading it live would mean a report written over a minute of
  // thinking describes a board that has moved on since.
  const context = useMemo(() => attachment(subject), [subject]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  useEffect(() => {
    box.current?.focus();
  }, []);

  async function send() {
    if (!message.trim() || status === "sending") return;
    setStatus("sending");
    setStatus(await submit({ kind, message, contact, context }));
  }

  const link =
    "underline decoration-rule underline-offset-4 hover:text-ink hover:decoration-current";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[color-mix(in_oklab,var(--bench)_86%,transparent)] p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-title"
    >
      <div className="panel settle my-auto flex w-full max-w-xl flex-col gap-5 rounded-xl border p-6 sm:p-8">
        <div className="flex items-baseline justify-between gap-4 font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
          <span id="report-title">report a problem</span>
          <button type="button" onClick={onClose} className={link}>
            close
          </button>
        </div>

        {status === "sent" ? (
          // Nothing to do here but leave, so the panel says so and stops being
          // a form. Keeping the textarea alive invites a second identical send.
          <div className="flex flex-col gap-4">
            <p className="text-[17px] leading-relaxed">
              Sent — thank you. If a puzzle is wrong, this is genuinely how it
              gets fixed.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="self-start rounded border border-rule bg-panel px-4 py-1.5 font-mono text-[12px] font-semibold uppercase tracking-[0.14em] transition-[transform,border-color] duration-100 hover:-translate-y-px hover:border-muted"
            >
              back to the game
            </button>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              {KINDS.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setKind(option)}
                  aria-pressed={kind === option}
                  className={[
                    "rounded border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors duration-100",
                    kind === option
                      ? "border-brass text-brass"
                      : "border-rule text-muted hover:border-muted hover:text-ink",
                  ].join(" ")}
                >
                  {KIND_LABELS[option]}
                </button>
              ))}
            </div>

            <label className="flex flex-col gap-2">
              <span className="sr-only">What happened</span>
              <textarea
                ref={box}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                maxLength={MESSAGE_LIMIT}
                rows={5}
                placeholder={
                  kind === "chemistry"
                    ? "Which reaction, and what should it have been?"
                    : "What happened, and what were you doing?"
                }
                className="w-full resize-y rounded border border-rule bg-bench p-3 text-[15px] leading-relaxed outline-none placeholder:text-muted focus:border-muted"
              />
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                email, if you want an answer — optional
              </span>
              <input
                type="email"
                value={contact}
                onChange={(event) => setContact(event.target.value)}
                autoComplete="email"
                className="w-full rounded border border-rule bg-bench px-3 py-2 font-mono text-[13px] outline-none focus:border-muted"
              />
            </label>

            {/* Never filled by anyone who can see the form, so anything in it
                came from something that cannot. Hidden from assistive tech and
                skipped by tab, so it is invisible to people rather than merely
                off-screen. */}
            <input
              type="text"
              name="website"
              tabIndex={-1}
              autoComplete="off"
              aria-hidden
              className="hidden"
              onChange={() => {}}
              value=""
            />

            <div className="flex flex-col gap-2 border-t border-rule pt-4">
              <button
                type="button"
                onClick={() => setShowing((current) => !current)}
                className={`self-start font-mono text-[11px] uppercase tracking-[0.12em] text-muted ${link}`}
              >
                {showing ? "hide" : "show"} what is attached
              </button>
              {showing && (
                <pre className="max-h-56 overflow-auto rounded border border-rule bg-bench p-3 font-mono text-[11px] leading-relaxed text-muted">
                  {context}
                </pre>
              )}
              <p className="text-[13px] text-muted">
                The day, the target and your moves go with this, so a wrong
                reaction can be reproduced. Nothing else about you is attached.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={send}
                disabled={!message.trim() || status === "sending"}
                className="rounded border border-rule bg-panel px-4 py-1.5 font-mono text-[12px] font-semibold uppercase tracking-[0.14em] transition-[transform,border-color] duration-100 enabled:hover:-translate-y-px enabled:hover:border-muted disabled:opacity-35"
              >
                {status === "sending" ? "sending" : "send"}
              </button>
              {status === "failed" && (
                <span className="text-[13px] text-muted">
                  That did not go through. Your message is still here — try
                  again?
                </span>
              )}
              {status === "unconfigured" && (
                <span className="text-[13px] text-muted">
                  Reporting is not switched on for this build, so there is
                  nowhere for this to go yet.
                </span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
