# Daily Chemistry Puzzle — Project Brief

## What this is

A free, non-profit daily browser puzzle: Little Alchemy's crafting loop with real
chemistry as the combination rules. Each day the player is dealt a small palette of
species and one target compound, and has to find **five different kinds of reaction
that produce it**. Aimed at curious people and high-school students — accessible
enough to play without a textbook open, rigorous enough that everything you build
is a real, balanced reaction.

Similar existing games (Chemidle, Chemdle, Synthordle) are organic-chemistry
revision tools for people who already know chemistry. This is deliberately
general/inorganic and beginner-facing.

## Core mechanic

- The player holds an inventory, starting with the day's palette (up to ~15 species).
- Selecting 1–2 species and firing produces a new species, which is added to the
  inventory. Intermediates are **reusable, not consumed** — no stoichiometric
  resource management.
- A **way** is scored when a reaction's product is the target *and* its rule
  template has not been scored yet. Five distinct rules wins the day; every further
  rule is bonus, which is what a leaderboard would rank.
- No fail state and no move budget. Dead ends cost nothing but time.

Two rules keep the mechanic from degenerating:

- **One move, one product.** A triprotic acid with a base offers three salts and the
  engine has no amounts with which to choose between them, so a multi-product mix
  pauses and asks. Taking all three would hand over three species for one move and
  score a way nobody picked.
- **The target is a trophy, not a reagent.** `Na2SO4 + H2SO4 -> NaHSO4` followed by
  `NaHSO4 + NaOH -> Na2SO4` is two real reactions and one fake way: it consumes the
  target to make the target. Any route needing the target is circular, so refusing
  it as an input costs no legitimate route.

  It does, however, cost *ways*, and that is not the same thing. Refusing the
  target as an input is a statement about reachability, not about one reaction:
  a substrate whose every route runs through the target is unobtainable too, and
  the rule that needed it is circular at one remove. On a day whose target sits
  at the root of a family this can take most of the family with it — bar CO2 and
  every carbonate goes, which is three of that day's five ways. So any count of
  "how many ways does this hand have" must be taken against the closure with the
  target barred. Counting it against the plain closure is how a CO2 day shipped
  to CI asking for five and offering two.

## Scoring counts rules, never routes (the load-bearing decision)

H2CO3 has 813 routes in the network and 812 of them are the same acid displacement
with the spectator ion swapped. Counting routes grades a lookup as a masterpiece.
So everything — the win condition, the difficulty grade, any leaderboard — counts
**distinct rule templates**.

A rule counts as *accessible* only if all of its substrates are species a student
could plausibly name (`chem.rules.commonness`). A route through MgCrO4 is real
chemistry and a bad puzzle.

## Feedback

Feedback is about the *product*, never about whether a move lies on a path to the
target — signalling path membership would turn the puzzle into a guided walk. The
player sees what a reaction produced, whether it was the target, and whether that
rule was new. Dead ends are remembered so a pair never has to be rediscovered.

At the end the game shows one worked reaction for **every** way, including the ones
missed. It is a teaching game; the last screen is the lesson.

But winning is not the end of the day, and the sheet used to behave as though it
were: it printed the instant the fifth slot filled, which handed over every bonus
way the player had not reached — the ways that are the only thing a leaderboard
could rank. So the win is announced instead, and the player picks. Keep the bench
open and hunt, or print the sheet and close the day. Printing is the same door
giving up uses and shuts the same way, because a way copied off the sheet is not
a way anybody found. The choice is only offered when something is left; a rack
already holding every way has nothing to decide, so the sheet simply prints.

## Representation

Formula-level, **not** structural. Species are formula strings (`NaCl`, `CuSO4`,
`Ca(OH)2`) — SMILES is the wrong abstraction here and should not be used.

Use **ChemPy** (not RDKit): `Substance.from_formula` parses formulas including
nested parentheses and charge; `balance_stoichiometry` returns integer coefficients.
Underdetermined systems return parametrized results — reject any reaction whose
coefficients are not clean positive integers. Never call `Reaction.from_string` on
user input (it uses `eval`).

Each species record carries: formula, compound class (metal, nonmetal, basic oxide,
acidic oxide, acid, base, salt, hydride), constituent ions with charges, display
name, and state.

## Reaction rules

Rules are generic over **compound classes**, not over individual species. Products
come from ion recombination plus criss-cross of charges. Thirty-one templates cover
the whole network; `chem.rules.catalogue` is the one place they are listed, and it
gives each a stable slug so exports, saves and puzzle bundles have something durable
to key on while the prose wording stays free to change.

    elements in   oxidation · binary_salt_synthesis · hydrogenation · hydride_synthesis
    water in      anhydride_hydration · basic_oxide_hydration · metal_with_water ·
                  hydride_dissolution
    acid/base     neutralisation · acid_with_basic_oxide · base_with_acidic_oxide ·
                  oxide_with_oxide · metal_with_acid · acid_displacement
    salts         double_displacement · salt_with_base · metal_displacement ·
                  halogen_displacement · oxide_reduction · aluminothermic_reduction ·
                  halogen_disproportionation
    acid salts    partial_neutralisation · salt_with_parent_acid · acid_salt_with_base
    chromate      chromate_acidification · dichromate_alkalisation
    on heating    unstable_decomposition · hydrogencarbonate_decomposition ·
                  carbonate_decomposition

Twenty-nine slugs, not thirty-one, and the gap is deliberate. Ammonia writes two
equations nothing else writes — it takes a proton without giving water, and it
leaves a salt as a gas rather than as a precipitate — so it needs two templates
of its own, but neither is a second thing to discover. They are catalogued under
`neutralisation` and `salt_with_base`, the rules they are special cases of.
Scored separately they were a free way on most days, because NH4OH is ammonia
plus water and any palette holding NH3 could reach both halves of the same idea.

`chem.validate` checks that every reaction the engine can emit came from a
catalogued template, so a rule added without a slug surfaces as a failed check
rather than as an unrecognised string in an export — and that any slug two
templates share is one of the two declared merges, since an undeclared collision
would fold two rules together silently.

## Data tables (the entire curation burden)

1. **Ion charges / valences** — the backbone; nothing works without it (~30 ions plus
   common oxidation states for multi-valent elements)
2. **Solubility table** — gates double displacement (does it precipitate?)
3. **Activity series of metals** — gates metal + acid and metal + salt displacement
   (*not* electronegativity — it does not predict these)
4. **Metal / nonmetal classification** — also determines whether an oxide is basic
   or acidic
5. **Unstable products** — auto-decompose (H₂CO₃ → CO₂ + H₂O, H₂SO₃ → SO₂ + H₂O,
   NH₄OH → NH₃ + H₂O)
6. **Strong / weak acids and bases** — gates displacement of the weaker by the stronger
7. **Reducibility of oxides** — gates carbon and aluminothermic reduction
8. **Commonness** — which species a beginner could name. Not chemistry, but it is what
   separates a puzzle from a lookup, so it is curated with the same care.

## Puzzle generation

Target-first, offline. Choosing a palette independently of the target produces
unsolvable days.

The **cut** is the difficulty dial, and it is independent of which target is chosen:
it is the depth at which the backward walk stops building and starts dealing. At cut
0 the palette is bare elements and the player rebuilds everything; at cut 2 they are
handed acids and bases and the day is short. Default 1. Resolving all the way to
elements every time would deal roughly the same two dozen species daily and waste
the variety in a 1183-species network.

1. Group the target's routes by rule. Each rule is one way.
2. For each rule, resolve one route's substrates backward until every branch bottoms
   out at the cut. That leaf set is what the way costs. A branch that dead-ends above
   the cut — a common product with no common route of its own — is skipped rather
   than dealt, so a palette never contains a starting material nobody could have
   expected.
3. Greedily buy the ways whose leaf sets are cheapest, keyed on new species first and
   **foreign elements** second — foreign meaning elements the target does not itself
   contain, which is what stops a baking-soda puzzle dealing `Cr` and `CuBr2`. Stop at
   the palette budget. This is set cover, not backtracking: at the budget it keeps the
   best coverage found rather than retrying route choices, so it terminates predictably.
4. **Verify forward.** Rebuild the network from the chosen palette and count the rules
   it really enables. Step 2 reasons about one route at a time and cannot see whether
   substrates are co-buildable, so its count is only a proposal; the forward number is
   what ships.

Difficulty rotates over the week the way a crossword does — gentle Monday, hardest
Friday. Hard targets have *few* ways, that being what makes them hard, so demanding
five would exclude every hard compound and Friday would never generate: the ask
scales instead, five where five exist and **four** at the floor. Never three —
a hand worth three is not a puzzle, and the day is better left with a gap.

The floor is the variety dial, and it is worth more than the number suggests.
Only 31 of the 99 playable medium targets offer a fifth way *on the grading
pass*, so a floor of five threw two thirds of the medium catalogue away and left
a weekly draw picking from 31 compounds. The other 68 still deal hands worth
five, because the grading pass counts under the commonness gate across the whole
network while a player meets the closure of the dealt palette, which is larger.
So the floor is what admits them and the forward count is still what ships.

A day is seeded off its date ordinal rather than shuffled, so a puzzle can be
regenerated after the fact — to reproduce a bug report, or to rebuild a month —
without disturbing yesterday's.

## The two-month window

A seed spreads the *choices* evenly and remembers nothing, so the draw repeated
itself — the same compound twice in one week, which a player notices and a seed
cannot see. So the picker reads the calendar: **a day will not deal a target any
of the previous 62 days dealt.** Backwards only, because days after the one being
dealt were not inputs when it was first dealt, and reading them would cost the
property that a date rebuilds its own puzzle.

The same 62 days decide what is deleted. The weekly job prunes every bundle older
than the window, and the two numbers are one number (`chem.puzzle.RECENT_DAYS`)
because a day can only avoid what it can still read: anything deleted early is a
repeat waiting to happen, anything kept late is kept for nothing. Deleting is safe
because nothing reads an old bundle — the front end serves exactly one day, the
most recent that is not in the future, and has no archive — and git keeps them all
anyway. Two rails on the delete: future days are never touched, and neither is the
day the site is currently serving, even if the calendar has run so dry that it
falls outside the window.

**The window yields; the day does not.** Where no unused target deals a hand worth
having, the day repeats one and says so in the log, because a missing day is the
worse failure: the site would serve the most recent day it has, repeating
yesterday's entire hand rather than one target. Friday lives there permanently —
7 of the 58 hard targets deal a usable hand and a window holds about 9 Fridays, so
on hard the rule is not tight but unsatisfiable, and about one Friday in three
repeats. That is a fact about how few hard compounds have four ways, not about the
window; the fix, when there is one, is a wider hard catalogue.

## Layout, and why there is no runtime backend

    backend/    Python. Chemistry, network, grading, generation, and a terminal
                version of the game (play.py) for feeling out whether a hand is fun
                before it reaches the browser.
    frontend/   Next.js. Plays a dealt hand. Contains no chemistry.

Backend layering: `formulas` (pure syntax) → `data` (tables) → `rules` (decisions) →
`validate` → `balance` (ChemPy). **Rules may read data; data never reads rules.**

A dealt hand's whole closure is a few tens of kB — every species reachable from the
palette and every reaction between any two of them, equations already balanced —
against 8.6 MB for the full reaction list. So `chem.puzzle` writes one JSON bundle
per day into `frontend/public/puzzles/` and the browser plays it offline. "What
happens if I mix these" is a lookup rather than a rule engine the browser would have
to re-implement, which is the whole reason the chemistry can stay in one language.

The bundle ships its own answers deliberately: the end screen has to work when the
network does not. What that protects is the *integrity* of a game, not the secrecy of
its solutions. Saves store the move log and nothing derived from it, and restoring
replays that log through the same reducer that validated the moves live — so a
hand-edited save cannot put species into play that the bundle never produced.

There is exactly one server function, and the heading above still holds: `POST
/api/report` forwards a player's report to Resend. It carries a sentence in the other
direction and nothing else — no chemistry runs on it, nothing the game needs comes
back through it, and when it is unconfigured or down every page plays as before. A
second endpoint is not a precedent; it is a decision to make again.

## Scope

In: general and inorganic chemistry at school level. Out (for v1): organic synthesis,
amphoteric oxides (Al, Zn — tagged and excluded, to be added deliberately later),
reaction conditions and kinetics, equilibria.

Reaction plausibility comes from curation and the tables above — **never** from an ML
reaction predictor at runtime. A puzzle needs a crisp, guaranteed-correct answer.
