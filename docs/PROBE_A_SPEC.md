# PROBE-A: the adaptive unified agent

One agent, all instruments onboard, each activating only when its runtime
trigger fires — the space-probe framing made literal. The probe variant
campaign (probe1 through 5.3.2) was, in hindsight, the discovery of each
mechanic's activation condition; PROBE-A encodes them.

## Core (always on)

- Round 1 loop: explicit situation belief + RULE belief, stagnation-as-
  contradiction, active experimentation (probe1; won MiniHack, tied TextWorld).
- Novelty progress signal: progress = score gain OR world-state change, never
  score alone (probe5.1; fixes the terminal-reward thrash seen on TextWorld and
  ARC).
- Anti-loop cooldown: an action that just produced a no-op sits out ~3 steps;
  never a permanent ban (probe5.1/5.3.1; hard blocks broke winnable games).
- Stuck nudge acts, never senses: when stagnating, force an untried
  world-changing action; do not examine more (the rejected surprise gate's
  failure mode, and probe3's bug).

## Instruments (adaptive, deterministic Python triggers — never LLM judgment)

1. MAP of places (probe5.2). Bookkeeping always on; the map section is
   INJECTED into the prompt once >= 2 distinct rooms/locations have been seen
   (partial observability detected). Fully observable grids never trigger it.
   Evidence: doubled ScienceWorld; cost-free on TextWorld; meaningless on ARC.

2. ACTION LEDGER (probe5.3). Bookkeeping always on (per-action outcome
   tallies from observed deltas); the ledger section is INJECTED once the
   recorded outcomes carry signal (>= 3 actions with recorded outcomes, or any
   action produced a resource/achievement/score effect). Prompt pins it as
   ground-truth physics.
   Evidence: turned ARC beliefs from hallucination to grounded physics.

3. SYSTEMATIC PROBE PHASE (probe5.3.2). Runs only when the action interface
   is OPAQUE, detected at step 0 by regex (ids like ACTION1..7 with no
   semantic names): every available action gets two deterministic tries (no
   model calls) before the ledger is trusted.
   Evidence: fixed the exploration collapse on ARC; unnecessary where actions
   are named (TextWorld/ScienceWorld/Crafter verbs).

## Deliberately excluded (documented negatives)

- Hypothesis-set + plan-commit + elimination as always-on machinery (probe2:
  0.29 on TextWorld, overhead without benefit).
- LLM-judged mode switching (the surprise gate, Session 058: gating on model
  judgment amplified sensing).
- Permanent action bans (probe5-hard, 5.3: broke context-dependent actions).
- Examine-heavy stuck responses (probe3: raised sensing share to 0.42).

## Per-environment adapters

The controller is shared; each boss maps its observation/action interface:
TextWorld (rooms from admissible-set changes; commands named), ScienceWorld
(rooms from headers; commands named), Crafter (entity types as the "seen
world"; yields as ledger outcomes; actions named), MiniHack (dungeon glyphs;
actions named), ARC (fully observable grid so no map; opaque ids so probe
phase + ledger).

## Acceptance protocol

Run probe_a on TextWorld (expect: tie ~0.55, no harm), ScienceWorld (expect:
hold ~probe5.2's 26.6), Crafter (expect: hold >= probe_cf's level; the stored
n=100 trio is the reference), MiniHack (codespace; expect: hold >= 0.20).
PROBE-A must never lose to the per-environment specialist it absorbs; ties at
lower variance are acceptable, regressions are not.
