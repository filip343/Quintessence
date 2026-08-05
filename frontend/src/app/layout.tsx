import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono, Newsreader } from "next/font/google";
import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

/**
 * Applies a stored theme choice before the first paint.
 *
 * It has to be inline and it has to run before the body renders, or a reader
 * who chose light on a dark machine gets a black flash on every navigation.
 * Nothing else belongs in here.
 */
const APPLY_THEME = `try{var t=localStorage.getItem("fiveways:theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

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

export const metadata: Metadata = {
  title: "Five Ways - a daily chemistry puzzle",
  description:
    "Find five different reactions that make the day's compound. Real inorganic chemistry, no textbook needed.",
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
      </body>
    </html>
  );
}
