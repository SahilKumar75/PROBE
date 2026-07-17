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
src/probe/
  constants.py
  stage0/
    boss_i0.py            internal hidden rule environment used as a smoke test
    minigrid_env.py       external benchmark wrapper (MiniGrid GoToObject)
    minigrid_policies.py  random, heuristic and language model baselines
    minigrid_runner.py    evaluation loop and trace capture for the external boss
    runner.py             evaluation loop for the internal boss
    tracing.py            trace schema and writers
    gemini_client.py      language model backend
    groq_client.py        language model backend
    ollama_client.py      local language model backend
    openrouter_client.py  language model backend with automatic model fallback
scripts/
  run_stage0.py             run the internal boss evaluation
  run_stage0_minigrid.py    run the external MiniGrid evaluation
  aggregate_stage0_minigrid.py  aggregate batched runs
config/
  stage0_protocol.md      locked Stage 0 evaluation protocol
docs/                     research notes tracked alongside the code
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
