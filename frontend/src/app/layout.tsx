import type { Metadata } from "next";
import Script from "next/script";
import { Archivo, IBM_Plex_Mono, Newsreader } from "next/font/google";
import { Report } from "@/components/Report";
import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

/**
 * Applies a stored theme choice before the first paint.
 *
 * It has to be inline and it has to run before the body renders, or a reader
 * who chose light on a dark machine gets a black flash on every navigation.
 * Nothing else belongs in here.
 */
const APPLY_THEME = `try{var t=localStorage.getItem("quintessence:theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

/**
 * Three faces, three jobs.
 *
 * Archivo is the printed reagent label and the periodic-table cell: a tight
 * grotesque, used only for the target and the section marks. Newsreader is the
 * teaching voice — every sentence that explains something. Plex Mono is the
 * instrument: formulas, equations, counts, and the controls, which should read
 * as keys on a piece of lab equipment rather than as web buttons.
 */
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const UMAMI_ID = process.env.NEXT_PUBLIC_UMAMI_ID;

const TITLE = "Quintessence - a daily chemistry puzzle";
const DESCRIPTION =
  "Find five different reactions that make the day's compound. Real inorganic chemistry, no textbook needed.";

export const metadata: Metadata = {
  // Open Graph needs absolute urls, and the only place that knows the domain
  // is the deployment. Set NEXT_PUBLIC_SITE_URL there; falling back to
  // localhost keeps `next build` quiet and produces a link preview that is
  // wrong only in development, where nobody is sharing links.
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: TITLE,
  description: DESCRIPTION,
  applicationName: "Quintessence",
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    siteName: "Quintessence",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${archivo.variable} ${newsreader.variable} ${plexMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col">
        {/* First thing in the body, not a child of <html>: React 19 rejects a
            script there and the resulting hydration error takes the whole tree
            down with it. Here it still runs before anything paints. */}
        <script dangerouslySetInnerHTML={{ __html: APPLY_THEME }} />
        <ThemeToggle />
        {children}
        {/* Here rather than inside a page, so it is on every one of them —
            including the ones that exist because something already went wrong,
            which are exactly the pages worth being able to report from. What it
            attaches comes from whichever page is mounted; see `lib/report`. */}
        <Report />
        {/* Absent unless a website id is configured, which is what keeps
            development out of the numbers: the variable is set on the
            deployment only, so localhost never has a tracker to report to and
            needs no domain filtering to stay quiet. Cookieless and carrying no
            identifier of any kind — see `lib/analytics`. */}
        {UMAMI_ID && (
          <Script
            defer
            src="https://cloud.umami.is/script.js"
            data-website-id={UMAMI_ID}
          />
        )}
      </body>
    </html>
  );
}
