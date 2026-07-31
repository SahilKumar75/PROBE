# PROBE: A Hypothesis Driven Agent Architecture for Novel Environment Adaptation

PROBE, short for Proactive Rule Oriented Belief Engine, is a research prototype that studies how a language model agent can adapt to a genuinely new environment by discovering its hidden rules through interaction, instead of relying on memorized patterns or static retrieval.

The idea is a reasoning loop that forms an explicit belief about how the environment works, tests that belief by acting, detects when an observation contradicts the belief, and then revises the belief. The agent chooses the action that reduces the most important current uncertainty.

## Status

This is active research code, not a finished product. It grows in stages, and the commit history is written to read like a research log rather than a release changelog.

## Research question

How can an agent learn the rules of a new environment quickly, instead of relying on memorization, static retrieval, or generic reflection, and can it recover when those rules change during an episode.

## Scope of the belief

The belief in PROBE ranges over the environment rules and dynamics, meaning how the world works, not over object locations or a fixed skill set. Contradiction detection and belief revision under changing rules are the intended core of the contribution.

## Repository layout

```
src/probe/                the agent and environment code, one package per boss
  stage0/                 baseline loop on MiniGrid, plus the LLM backend clients
  multifactor/ competing/ rule_shift/ probe_progress/ relational/ mixed/
                          the original internal diagnostic bosses (I1 to I7)
  benchmarks/ bench_induction/ bench_adaptation/
                          the v2 internal benchmarks (rule induction, rule
                          adaptation) with shared baseline/reflexion/probe
                          agents and deterministic no-API solvers
  textworld_boss/         hidden-rule TextWorld external (baseline, reflexion,
                          probe1 and the probe2-5.2 variant line)
  minihack_boss/          MiniHack River-Narrow external (hidden crossing rule)
  crafter_boss/           Crafter external (the headline anchor, n=100)
  arc_boss/               ARC-AGI-3 external, offline on the official ARCEngine
                          example games (interpreter, agents, runner)
scripts/
  run_*.py                one runner per boss (textworld, minihack, crafter,
                          arc, internal suites)
  run_tw_chunked.sh       parallel launchers: many single-worker processes over
  run_mh_chunked.sh       disjoint seed chunks (tatsu and NLE are not
  run_arc_chunked.sh      thread-safe), logs land in runlogs/
  compute_cis.py          recompute confidence intervals from saved traces
  analyze_mh.py           MiniHack trace analyzer
config/                   locked evaluation protocols
docs/                     research notes tracked alongside the code, including
                          research_insights.md and the codespace setup guide
traces/                   per-step CSV traces (gitignored, force-add results)
outputs/                  per-run summary JSON (gitignored, force-add results)
runlogs/                  local run logs and pid files (gitignored; the tracked
                          minihack per-seed logs live in runlogs/minihack/)
```

## Setup

Requires Python 3.10 or newer.

```
pip install -e .
```

## Running Stage 0

Stage 0 establishes the baseline loop, reproducible runs, and trace capture on the external benchmark MiniGrid GoToObject 6x6 N2. The locked protocol is 10 seeds and 20 episodes per seed, giving 200 episodes per variant.

Random baseline:

```
python scripts/run_stage0_minigrid.py
```

Language model baseline with OpenRouter:

```
export OPENROUTER_API_KEY=your_key_here
STAGE0_VARIANTS=plain_llm_agent python scripts/run_stage0_minigrid.py
```

Long runs may be executed in fixed batches and aggregated afterward, following config/stage0_protocol.md.

## Environment variables

```
OPENROUTER_API_KEY   required for the plain_llm_agent baseline
OPENROUTER_MODELS    optional, a comma separated fallback chain of model ids
STAGE0_VARIANTS      optional, comma separated subset of variants to run
STAGE0_BATCH_SEEDS   optional, comma separated seed subset for a batch
STAGE0_BATCH_EPISODES optional, comma separated episode subset for a batch
STAGE0_BATCH_ID      optional, label attached to batch outputs
```

## License

MIT. See LICENSE.
