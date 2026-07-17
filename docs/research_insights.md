# Research Insights

This document collects research-relevant insights that emerge during planning and prototyping.

The purpose is to preserve material that may later be useful in:

- paper drafting
- thesis writing
- experiment design
- methodology justification
- related-work positioning

---

## Insight 001: The core problem is novel environment adaptation, not generic memory

### Observation

The original project started broadly in LLM and agentic AI, with possible themes such as memory, updating, context, grading, decision-making, MCP, Neo4j, and graph-based systems.

After narrowing the gap, the strongest target problem became:

`How can an agent learn the rules of a new environment quickly instead of only relying on memorized patterns, static retrieval, or generic reflection?`

### Why it matters

This sharpened the project away from crowded directions such as generic memory systems, generic self-reflection, graph databases as infrastructure choices, and broad layered architectures without a new mechanism.

### Paper relevance

This can support the paper's problem statement and motivation section.

---

## Insight 002: ARC-AGI-3 is a motivating stress test, not the full paper topic

### Observation

ARC-AGI-3 was adopted as a reference problem because it highlights a deep weakness in current systems: failure in novel, interactive environments that require probing, inference, and online model-building.

However, the project direction was intentionally not reduced to "solve ARC-AGI-3." Instead, ARC-AGI-3 is treated as a final stress test for a broader capability: novel environment adaptation.

### Why it matters

This avoids overfitting the research contribution to one benchmark and keeps the paper focused on a general mechanism rather than a single evaluation target.

### Paper relevance

This belongs in the framing section and helps justify why multiple intermediate environments and benchmarks are used before the final evaluation.

---

## Insight 003: The candidate contribution is a mechanism-centered architecture

### Observation

A generic layered diagram is not enough to be a meaningful research contribution. The architecture only becomes publishable if it introduces a mechanism such as explicit hypothesis formation, belief storage with evidence, contradiction detection, belief revision, or exploration for information gain.

### Why it matters

The likely novelty is not memory alone or graphs alone, but the interaction between candidate beliefs, contradiction handling, and exploratory action selection.

### Paper relevance

This supports the system overview and contribution framing.

---

## Insight 004: Build-first methodology is part of the research method

### Observation

Instead of drafting the full paper first, the project adopted a build-first workflow: define the research gap, design a staged roadmap, lock the experiment protocol, prototype a minimal environment, inspect failures, and use observed failures to motivate the next architectural addition.

### Why it matters

This reduces the risk of writing a novelty story that is not grounded in actual experimental evidence. It also creates a stronger empirical narrative: what failed, what changed, and why the change mattered.

### Paper relevance

This can inform the methodology section and help explain why the paper includes staged task escalation.

---

## Insight 005: Internal and external bosses serve different scientific roles

### Observation

The roadmap initially leaned too heavily on internal/custom environments. This was corrected by introducing a hybrid ladder: internal bosses for controlled diagnosis, external bosses for transfer and credibility, and ARC-AGI-3 as the final stress test.

### Why it matters

Internal environments help isolate failure modes and justify incremental capability upgrades. External benchmarks prevent the project from overfitting to self-designed tasks.

### Paper relevance

This is useful when justifying the evaluation design and explaining why both handcrafted and benchmark tasks are used.

---

## Insight 006: Graph-based memory should be conditional, not assumed

### Observation

Graph-based memory was considered early because of interest in Neo4j and structured representations. However, the roadmap now treats this as conditional: enter Stage 5 only if earlier stages reveal clear relational failures that flatter belief memory cannot handle well.

### Why it matters

This keeps the project honest and avoids forcing graph complexity into the system before it is empirically justified.

### Paper relevance

This can help explain design restraint and why graph-based structure is tested as a necessity rather than treated as a default assumption.

---

## Insight 007: Stage 0 established the experimental pipeline, not the core claim

### Observation

The first runnable prototype implemented an internal Stage 0 boss, step-level trace logging, a baseline runner, and summary metric generation. This validated the experiment pipeline end to end.

### Why it matters

Before this run, the evaluation contract existed only on paper. After this run, the project had a runnable environment, reproducible execution, saved traces, and per-variant summaries.

### Paper relevance

This supports the reproducibility and instrumentation story, even though it is not yet strong evidence for the final research claim.

---

## Insight 008: Boss I0 is useful as a smoke test, but too easy as serious evidence

### Observation

On the first Stage 0 internal boss, random policy achieved high success and the placeholder plain_llm_agent achieved even higher success. The important lesson was not that one agent won but that the task itself is too easy to provide strong discriminative evidence.

### Why it matters

This is an early negative finding: a benchmark can be aligned with the research idea yet still be too easy to support a strong claim. BossI0 is now better interpreted as a smoke test, debugging environment, and regression check.

### Paper relevance

This strengthens methodological credibility by showing that weak evidence was not overclaimed, and it motivates the move to stronger external environments.

---

## Insight 009: Early benchmark choice affects the entire research path

### Observation

The roadmap became meaningfully more concrete only after external benchmarks were selected by stage: Stage 0 MiniGrid, Stage 1-2 TextWorld, Stage 3 MiniHack provisional, Stage 4 Crafter, Stage 6 ARC-AGI-1, Stage 7 ARC-AGI-2, Final Boss ARC-AGI-3.

### Why it matters

Benchmark selection determines what kinds of failures can be observed, what capabilities are rewarded, which architectural components are justified, and how credible the eventual evaluation will be.

### Paper relevance

This can help explain the staged benchmark ladder and why the evaluation was designed as an escalation from controlled tasks to ARC-like abstraction.

---

## Insight 010: The current main unresolved question is the locus of novelty

### Observation

The architecture direction is clear, but one major paper-level question remains open: which component contains the main novelty? Candidates include belief representation, contradiction detection, exploration policy, revision mechanism, or their interaction. This must be resolved before writing the final contribution section.

### Paper relevance

This is central to the final contribution statement and experimental design.

---

## Insight 011: External MiniGrid provides stronger evidence than the internal smoke test

### Observation

The external Stage 0 benchmark MiniGrid-GoToObject-6x6-N2-v0 produced a much sharper separation than the internal toy task. Random policy succeeded only rarely and the placeholder MiniGrid plain_llm_agent failed completely. This contrasts strongly with BossI0 where even random behavior performed well.

### Why it matters

This confirms that the internal boss is useful for debugging but weak as evidence, and that the external MiniGrid benchmark is much more appropriate for measuring meaningful adaptation progress.

### Paper relevance

This can support the argument for staged evaluation: start with internal smoke tests for debugging, then move quickly to external benchmarks for credible evidence.

---

## Insight 012: Simple heuristics can fail harder than random behavior

### Observation

On MiniGrid-GoToObject-6x6-N2-v0, a simple hand-written heuristic baseline failed completely while random behavior still achieved a small nonzero success rate.

### Why it matters

Naive deterministic rules can overcommit to the wrong behavior. The environment requires more than a shallow search pattern. Stronger baselines should not be assumed to arise automatically from common sense hardcoded rules.

### Paper relevance

This can support the claim that even apparently reasonable non-learning control policies are brittle in novel environments, and it strengthens the need for belief-oriented methods.

---

## Insight 013: LLM baseline evaluation can be limited by execution constraints, not only model quality

### Observation

A real Gemini-backed MiniGrid baseline was implemented and verified on a single action-generation call. However, the full Stage 0 external benchmark run failed because the free-tier API quota was too small for repeated per-step calls.

### Why it matters

Benchmark design is not only about task difficulty. Evaluation feasibility also depends on model-serving constraints such as latency, quotas, and per-step interaction cost.

### Paper relevance

This can support a practical discussion in the methodology or limitations section about interactive benchmark evaluation requiring either local inference, higher-throughput APIs, or reduced pilot protocols.

---

## Insight 014: Local models remove quota limits but not interaction cost

### Observation

Switching from cloud APIs to a local Ollama model removed quota limits, but the per-step interaction cost remained significant. A small timing probe showed each MiniGrid action took on the order of a few seconds.

### Why it matters

Local inference avoids rate limits but interactive environments can still be expensive because they require many sequential model calls. The constraint changes form from API quota bottlenecks to runtime and throughput bottlenecks.

### Paper relevance

This supports a practical argument that interactive LLM benchmarks may require pilot-scale protocols first, careful throughput planning, and a distinction between model capability and evaluation cost.

---

## Insight 015: PROBE is scaffolding, not a new neural architecture

### Observation

A key conceptual clarification emerged: PROBE does not change what is under the hood of the LLM. It changes how the system is organized and what it is forced to do at each step. The LLM is the engine. PROBE is the steering wheel, gearbox, and dashboard.

### Why it matters

This positions the contribution correctly. The novelty is in the architecture of the loop and the structure of the prompting, not in the weights or training procedure. This is a legitimate and publishable contribution, as shown by comparable work like ReAct, Reflexion, and Voyager.

### Paper relevance

This is critical for the contribution framing section. It must be stated clearly so reviewers understand what is and is not being claimed.

---

## Insight 016: The space probe analogy precisely captures the PROBE architecture

### Observation

The space probe analogy maps cleanly onto the PROBE loop. NASA decides the target, engineers select sensors, the probe gathers data, NASA scientists analyze and form theories, new instructions are sent, and the probe adjusts. PROBE merges the probe and NASA into one system: the agent does not just collect and react, it forms theories, tests them, and updates them.

### Why it matters

This analogy clearly distinguishes PROBE from a plain LLM agent (probe with no NASA) and from RL (probe that learns only through thousands of reward signals without explicit theory formation).

### Paper relevance

This is the paper's opening analogy. It belongs in the introduction and can anchor the motivation section. The candidate opening paragraph is:

"When NASA sends a probe to Mars, it does not just collect random data. It forms theories, tests them, and revises based on what it finds. Current LLM agents lack this structured loop. PROBE introduces it."

---

## Insight 017: The dark room analogy captures the exploration mechanism specifically

### Observation

A person waking in a dark room stretches an arm forward to find the wall. This is not random flailing. It is a deliberate probe action chosen to reduce the most important current uncertainty: the size of the room. Each touch updates the mental model. Each next step is chosen based on what is still unknown.

### Why it matters

This analogy isolates the exploration planner module. The agent does not just explore randomly. It asks: what action would teach me the most about what I currently do not understand? This is formally called information-gain driven exploration. It is implemented not with new math but with a prompt that forces the LLM to ask this question explicitly at every step.

### Paper relevance

This belongs in the exploration planner section of the method description and can also appear in the introduction as a second motivating example.

---

## Insight 018: PROBE's sensors are the environment's return values

### Observation

PROBE does not have hardware sensors. Its sensors are whatever the environment returns after each action: positions, object types, rewards, mission text, any observable value. The sensor suite changes by environment. The Observation Interpreter is the sensor processing unit that converts raw output into clean readable text for the LLM.

### Why it matters

This clarifies the architecture for readers who might ask: how does PROBE observe? The answer is simple. It reads what the environment returns. The novelty is not in the sensing but in what it does with that information.

### Paper relevance

This belongs in the Observation Interpreter module description and should be stated explicitly early to avoid confusion.

---

## Insight 019: The environment-agnostic goal is a long-term research direction

### Observation

A stronger version of PROBE would be dropped into any environment with only available action names and raw output format, discovering the meaning of all sensor signals through hypothesis-driven exploration alone. This would make PROBE truly universal rather than environment-specific. This is a real unsolved problem in AI research sometimes called zero-shot environment adaptation or active perception.

### Why it matters

This separates the current bachelor's paper scope from a longer research direction. The current paper can claim a more limited but achievable version: PROBE requires minimal environment bootstrapping and discovers more through exploration than a plain LLM. The universal version is future work.

### Paper relevance

This belongs in the discussion and future work section. It positions PROBE honestly in the broader research landscape without overclaiming.

---

## Insight 020: The strongest distinguishing claim against RL is episode efficiency and transparency

### Observation

PROBE is related to RL but distinct. RL learns implicitly through reward signals across thousands of episodes. PROBE reasons explicitly through language within a single episode. The knowledge lives in written text, is readable, and transfers through general language reasoning rather than environment-specific weights.

### Why it matters

This gives the paper a clean claim against RL baselines: PROBE adapts faster, within fewer interactions, with an inspectable trace of why. These three properties are measurable.

### Paper relevance

This belongs in the related work section when comparing to RL-based agent methods, and it should anchor the experimental evaluation design by ensuring the metrics include episode count to success, not just final success rate.

---

## Insight 021: Explicit belief + information-gain exploration is table stakes, not a contribution

### Observation

Align While Search (AWS, 2025) already implements an explicit belief state, information-gain-driven action selection, and test-time adaptation on a frozen LLM. These are exactly the properties PROBE was implicitly leaning on as "novel."

### Why it matters

Framing PROBE as "an LLM agent with an explicit belief that explores by information gain" would read to reviewers as a re-run of AWS. This framing must be abandoned. The contribution has to live somewhere AWS does not.

### Paper relevance

Do NOT foreground belief-existence or information-gain as the contribution in the abstract or intro. Treat them as shared machinery and move the novelty claim to the rule/revision/non-stationary axis (Insights 022-023).

---

## Insight 022: PROBE's belief is about RULES, not state or skills

### Observation

The cleanest way to separate the three nearest papers is by what the memory/belief is ABOUT. Voyager remembers reusable SKILLS (what it can do). AWS estimates STATE (where objects are, under a static-world assumption that factors out dynamics). PROBE should model the environment's RULES / dynamics (how the world works).

### Why it matters

This is PROBE's headline differentiator and it is defensible. AWS formalizes search as a single-state MDP with world dynamics removed; PROBE's entire point is to infer those dynamics. Different object of belief, different problem.

### Paper relevance

State this contrast explicitly in Related Work and in the problem formulation. The belief representation section must make clear the belief ranges over candidate RULES/dynamics, not locations.

---

## Insight 023: Contradiction-driven revision under non-stationary rules is the real niche

### Observation

AWS performs Bayesian SHARPENING: probability mass concentrates on the right hypothesis within a fixed hypothesis space, and its Limitations explicitly exclude non-stationary environments. PROBE's Rule-Shift boss (environment changes after the agent starts succeeding) is precisely that excluded case. PROBE must DETECT that a held rule is falsified and REPLACE it (revision), not merely reweight it (refinement).

### Why it matters

Refinement is not revision. The discrete "believed X -> X contradicted -> now believe Y", visible in the trace, is the behavior AWS does not target and cannot claim. This is the committed contribution of PROBE.

### Paper relevance

Center the method on the Contradiction Detector and Belief Revision Engine. Center the evaluation on recovery-after-rule-change, repeated-error rate, and interactions-to-adapt (efficiency). Use hidden/procedural rules and mid-episode rule shifts so that success reflects adaptation rather than memorized priors.
