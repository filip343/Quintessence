/**
 * The shape of a puzzle bundle, as written by the Python side
 * (`backend/chem/puzzle.py`).
 *
 * A bundle is closed under mixing: every reaction between any two species the
 * player could ever hold is already in `reactions`. So "what happens if I mix
 * these" is a lookup here, not a rule engine — the chemistry stays in one
 * language, and equations arrive balanced because balancing is ChemPy.
 */

export type Grade = "easy" | "medium" | "hard";

export interface SpeciesRecord {
  name: string;
  class: string;
  state: "s" | "l" | "g" | "aq";
  common: boolean;
  ions?: Record<string, number>;
}

export interface ReactionRecord {
  substrates: string[];
  products: string[];
  rule: string;
  /** Balanced, rendered by the backend. */
  equation: string;
  coefficients?: { substrates: number[]; products: number[] };
  note?: string;
}

export interface PuzzleBundle {
  version: number;
  target: string;
  name: string;
  grade: Grade;
  /** How many ways today asks for. */
  want: number;
  /** How many exist — always >= want, the surplus is the leaderboard. */
  ways: number;
  cut: number;
  palette: string[];
  species: Record<string, SpeciesRecord>;
  reactions: ReactionRecord[];
  /** One worked reaction per way, for the end screen. */
  answers: Record<string, ReactionRecord>;
}

/** Rule slugs are stable ids; these are what a player should read. */
export const RULE_NAMES: Record<string, string> = {
  oxidation: "burning in oxygen",
  binary_salt_synthesis: "metal + non-metal",
  hydrogenation: "hydrogen + non-metal",
  hydride_synthesis: "making a hydride",
  anhydride_hydration: "acidic oxide + water",
  basic_oxide_hydration: "basic oxide + water",
  metal_with_water: "metal + water",
  hydride_dissolution: "dissolving ammonia",
  neutralisation: "acid + base",
  partial_neutralisation: "acid + base, not enough base",
  acid_with_basic_oxide: "acid + basic oxide",
  base_with_acidic_oxide: "base + acidic oxide",
  oxide_with_oxide: "basic oxide + acidic oxide",
  metal_with_acid: "metal + acid",
  acid_displacement: "stronger acid drives out weaker",
  ammonia_with_acid: "ammonia + acid",
  ammonia_liberation: "ammonium salt + alkali",
  double_displacement: "salt + salt, something precipitates",
  hydroxide_precipitation: "salt + alkali, hydroxide drops out",
  metal_displacement: "more active metal pushes one out",
  halogen_displacement: "more reactive halogen pushes one out",
  halogen_disproportionation: "halogen + alkali",
  oxide_reduction: "reducing an oxide",
  aluminothermic_reduction: "more active metal reduces an oxide",
  salt_with_parent_acid: "salt + its own acid",
  acid_salt_with_base: "acid salt + more base",
  chromate_acidification: "chromate + acid",
  dichromate_alkalisation: "dichromate + alkali",
  unstable_decomposition: "it falls apart on its own",
  carbonate_decomposition: "heating a carbonate",
  hydrogencarbonate_decomposition: "heating a hydrogencarbonate",
};

export function ruleName(slug: string): string {
  return RULE_NAMES[slug] ?? slug.replace(/_/g, " ");
}

export const STATE_NAMES: Record<SpeciesRecord["state"], string> = {
  s: "solid",
  l: "liquid",
  g: "gas",
  aq: "in solution",
};

/**
 * The CSS hooks for a species' compound class.
 *
 * Hue places it on the acid-base axis and texture says what the substance is;
 * both live in `globals.css`. Classes arrive as prose from the Python side
 * ("basic oxide"), so they are slugged here — and filtered to letters and
 * hyphens, because a class name from a bundle should never be able to become
 * part of a selector that was not written by hand.
 */
export function speciesClass(record?: SpeciesRecord): string {
  if (!record) return "species";
  const slug = record.class.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z-]/g, "");
  return slug ? `species species-${slug}` : "species";
}

/** Reactions that consume exactly this unordered pair (or this one species). */
export function reactionsFor(
  bundle: PuzzleBundle,
  a: string,
  b?: string,
): ReactionRecord[] {
  const wanted = b === undefined ? [a] : [a, b].sort();
  return bundle.reactions.filter((reaction) => {
    if (reaction.substrates.length !== wanted.length) return false;
    const have = [...reaction.substrates].sort();
    return have.every((formula, index) => formula === wanted[index]);
  });
}
