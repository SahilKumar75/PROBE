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

---

## Insight 024: Backend access, not model quality, is the recurring bottleneck for interactive LLM benchmarks

### Observation

Across many sessions the real LLM baseline was blocked in a sequence of different ways: missing credentials, then Gemini free tier quota (429 RESOURCE_EXHAUSTED), then Ollama with no model installed, then a Groq 403 Cloudflare block, and now an unfunded OpenRouter account. The unfunded account has a signature pattern: paid models return HTTP 402 (insufficient credit) while free model variants return HTTP 429 (upstream rate limiting that unfunded accounts are subject to). A related client defect amplified the 402: the request reserved the model default of 16384 output tokens for what is only a one word action reply, which was fixed by capping max_tokens.

### Why it matters

An interactive benchmark issues one model call per step, so a modest 200 episode protocol becomes thousands of sequential calls. That volume interacts badly with free tier request caps and pay as you go balances. The limiting factor has consistently been the serving arrangement (credentials, quota, funding, access), not whether the model is capable of choosing MiniGrid actions.

### Paper relevance

Strengthens the limitations and methodology discussion: interactive LLM evaluation needs a serving plan decided up front (funded API, local inference with a pulled model, or a batched protocol under free tier caps), and per call token budgets should be bounded because the task output is tiny. This is distinct from Insight 013 (quota) and Insight 014 (local latency); it isolates funding and access as their own feasibility axis.

---

## Insight 025: A capable LLM given raw tensor observations collapses to a single repeated action

### Observation

In the first real Stage 0 validation batch (llama-3.3-70b as plain_llm_agent, 4 episodes on MiniGrid-GoToObject-6x6-N2-v0), the model chose forward on all 720 steps. It walked forward until the 180 step cap on every episode and never turned, for 0 success. The prompt gave only raw numeric encodings: direction as an integer, the front cell as a numeric triple, the grid shape, and a short action history, with no readable description of the visible layout or the target bearing.

### Why it matters

This degeneracy is an observation representation failure, not only a reasoning failure. With no interpretable signal about where the target is or that it is stuck against a wall, the model has no basis to turn, so it repeats its default action. This is confirmed to be the model and not a parser artifact: parse failures default to the done action, which would terminate episodes early, whereas 720 forwards mean the model itself emitted forward every time. It also repeats the pattern of Insight 012 (a naive policy can fail harder than random): random_policy scores 0.06 to 0.07 by occasionally starting adjacent to the target, while the always forward LLM scores 0.0.

### Paper relevance

Strong motivation for the Observation Interpreter as shared machinery that BOTH the baseline and PROBE must use. It is also a methodological warning: a plain LLM baseline fed raw observations is a confounded comparison, because PROBE would then appear to win by having readable observations rather than by belief formation, contradiction detection, and revision. For a fair test, give the baseline the same interpreted observation and let PROBE's advantage come only from the belief and revision loop. The raw observation LLM can optionally be reported as a separate naive reference point.

---

## Insight 026: Compete with AWS on efficiency by measuring the belief loop, not by adding a compression layer

### Observation

A tempting way to differentiate PROBE from AWS is token saving. The phrase hides two very different things. (A) Adaptation efficiency is an outcome: fewer interactions, steps, or tokens to adapt, produced by reusing and revising a belief instead of re-reasoning from scratch. (B) Prompt or context compression is an engineering layer that reduces tokens per call independent of the method. All four surveyed repos are type B: ponytail (minimal code generation), headroom (context compression), markitdown (document to Markdown), caveman (terse output style).

### Why it matters

Type A is a legitimate, measurable research claim that out positions AWS, which itself competes on token and step cost. The saving comes from PROBE's own mechanism, so it supports the thesis. Type B is not novelty for an architecture paper, is orthogonal to the rule shift niche, dilutes the single contribution, and can actively harm the study, since aggressive compression drops the very context needed to detect contradictions. Making token saving the main differentiator would repeat the Session 033 error of claiming shared machinery as the contribution.

### Paper relevance

Report adaptation efficiency as a supporting axis alongside success: interactions to adapt, tokens to recover after a rule change, and repeated error rate. Keep compression out of the contribution. Mention it at most as an implementation detail or an ablation (does cheap compression preserve adaptation), and cite the compression repos in Related Work under efficiency and systems rather than as novelty. The single contribution stays rule level belief plus contradiction driven revision under non stationary rules.

---

## Insight 027: Separate the action interface from the hidden rules, or the baseline is broken and the comparison is unfair

### Observation

MiniGrid-GoToObject-6x6 gives reward only when the agent emits the done action while standing orthogonally adjacent to the target object; the toggle action also ends the episode with zero reward. The original plain LLM prompt never stated this, so even a competent navigator could not score, and combined with raw numeric observations the model emitted forward on every step and timed out (Insight 025). Two separate defects were masquerading as one bad result: an unreadable observation and an undisclosed action interface.

### Why it matters

A baseline must be told the environment ACTION INTERFACE (what each action does and how success is declared). This is different from the environment HIDDEN RULES that PROBE is meant to discover. Conflating them produces a broken baseline and, worse, an unfair later comparison, because PROBE would appear to win by being handed interface facts that the baseline lacked. Stating go next to the target then declare done is fair interface disclosure; it is not rule inference.

### Paper relevance

The method section must distinguish interface knowledge (given to every agent) from rule knowledge (to be discovered). At Stage 0 both the baseline and PROBE receive the same readable observation and the same interface description. PROBE's advantage, tested later on hidden rule and rule shift tasks, must come only from belief formation and revision. As a side note, the done when adjacent mechanic is itself a small candidate hidden rule: a later PROBE demo could withhold it and show PROBE inferring do the done action near the target gives reward from experience, which a plain LLM without a belief loop fails to consolidate.

---

## Insight 028: The plain LLM baseline fails in exactly the two ways PROBE's modules target

### Observation

On the full Stage 0 external baseline (llama-3.3-70b, readable observation plus interface, 200 episodes), the plain LLM reached 0.59 success with a median of 5 steps, about 9x random (0.06 to 0.07) and far above the heuristic (0.0). Its 82 failures split into two clear modes: premature done (54 episodes), where the agent declares arrival while not adjacent to the target, and turning oscillation leading to timeout (28 episodes), visible as an 11 to 1 ratio of turn actions to forward actions across 7250 steps.

### Why it matters

These are not random failures; they map onto missing architectural components. Premature done is a belief error: the agent holds an unverified belief that it has arrived. A loop that maintains an explicit belief about position and verifies it before committing to the terminal action would suppress it. Turning oscillation is a memory error: with no memory that it already turned in this spot, the agent re-explores the same choice. A belief memory that records what has been tried removes the loop. So the plain LLM baseline provides a concrete, measured motivation for the belief and memory parts of PROBE, on the same backbone and the same environment.

### Paper relevance

Use this as the empirical hinge from baseline to method. The baseline is strong (so PROBE is not compared against a straw agent), yet its failures are systematic and nameable, and each names a PROBE module. Report premature done rate and turn to forward ratio as diagnostic metrics that PROBE should improve, alongside success and steps. Note that Stage 0 has fixed known rules, so it motivates the modules but does not yet demonstrate the rule level contradiction and revision contribution; that requires the hidden rule and rule shift stages.

---

## Insight 029: Naive structured belief prompting can backfire, and a gate that only blocks is not enough

### Observation

The first PROBE loop (v1) on GoToObject scored 0.17 against the plain baseline 0.59, a regression. The trace explains it. The plain baseline proposed the done action on 2.4 percent of steps; PROBE v1 proposed done on 57 percent of steps (514 of 904). The verify before done gate correctly blocked 513 of those false dones, so premature done nearly vanished, but each blocked done was overridden to a blind forward. That marched the agent into walls without ever navigating, so failures shifted from premature done to step budget timeout and success fell.

### Why it matters

Two lessons. First, asking the model to reason explicitly about arrival (an adjacent true or false field plus an action) made it over claim arrival and spam the terminal action, the opposite of the intended effect. Structure is not automatically better than a plain prompt. Second, a safety gate that blocks a bad action without substituting a good one merely converts one failure mode into another. The belief and verification idea is sound, shown by the single clean success that went belief, contradiction, verify, done, but the naive realization regressed below the unstructured baseline.

### Paper relevance

A cautionary, honest result for the method section. Report v1 as the negative result that motivates v2. The fixes are specific: tie the done decision to a verifiable observable (the model may choose done only when the cell directly ahead is stated to be the mission target), and on a blocked done substitute a belief driven approach action that navigates toward the believed target rather than a blind forward. Iterating from a documented regression strengthens credibility rather than weakening it.

---

## Insight 030: The first PROBE loop beats the plain baseline by eliminating the two named failure modes

### Observation

Over the full 200 episode protocol on the same backbone (llama-3.3-70b), PROBE v2 reached 0.865 success against the plain baseline 0.59, an increase of 27.5 points. The two failure modes that Insight 028 named are eliminated: premature done fell from 54 to 0, and the turn to forward ratio fell from 11 to 1 down to 1.3 to 1, so the oscillation is gone. The remaining 27 failures are all timeouts where the agent cannot relocate a target that is behind it. The verify before done gate fired 101 times and the belief was revised on 3353 of 6478 steps, so the mechanism is active, not incidental.

### Why it matters

It closes the loop from Insight 028: the baseline failures were named, a mechanism was built to target each, and the mechanism removed exactly those failures while raising success. This is the empirical arc a method section wants, and it is clean because the only change from the baseline is the loop, on the same model and environment.

### Paper relevance

Two honesty constraints must travel with this result. First, GoToObject has fixed known rules, so the belief here is about state, not rules; this validates the loop machinery and its benefit, but it is not the rule level contribution, which requires hidden rule and rule shift tasks. Second, part of the gain comes from the deterministic done gate and the approach helper, not only the belief and contradiction reasoning, so an ablation (belief only, gate only, full loop) is needed to attribute the 0.865 honestly. Report the win with both caveats stated, not hidden.

---

## Insight 031: On a navigation task the deterministic gate, not the belief reasoning, drives the gain, which tells us which task the contribution needs

### Observation

The four way ablation on GoToObject (200 episodes each, llama-3.3-70b): baseline 0.59, belief_only 0.54, gate_only 0.85, full 0.865. The deterministic gate carries almost the entire improvement. Belief reasoning alone (belief_only) is slightly below the plain baseline and adds only about 1.5 points on top of the gate. However, belief_only succeeds fastest when it does succeed (median 4 steps) and its dominant failure is spinning (turn to forward 16.7 to 1, 88 timeouts), so its beliefs are usable but it fails to commit them to action without the gate.

### Why it matters

Two lessons. First, a headline that says the belief loop drives performance would be false here; the win is hand coded navigation scaffolding, and that must be stated. Second, the reason is structural, not a failure of the belief machinery: GoToObject is a navigation task, so its success metric rewards motor execution, which a deterministic gate supplies, and it does not reward belief quality. The belief and contradiction reasoning cannot show its value on a task whose metric is walking efficiently.

### Paper relevance

This is the strongest argument yet for the task design of the actual contribution. The rule shift or hidden rule task must be built so that success depends on detecting a rule change and revising the belief, not on motor execution, because there no deterministic gate can substitute for the reasoning. The ablation also flags a concrete engineering gap to address in the method: belief to action, that is, getting the agent to commit to its belief, is currently the weak link and was masked at Stage 0 by the deterministic approach controller. Report the ablation as an honest attribution that redirects the evaluation rather than as a failure.

---

## Insight 032: Explicit rule belief helps a frozen LLM as rule complexity grows, on the learning axis; revision is the weak link

### Observation

On the rule shift boss with llama-3.3-70b, a scaling study over rule size (3 by 3, 6 by 6, 9 by 9) shows a clear crossover on pre shift learning accuracy. baseline versus PROBE pre shift: 0.80 versus 0.80 at 3, 0.38 versus 0.49 at 6, 0.25 versus 0.33 at 9. So PROBE ties when the rule is small enough for the model to hold implicitly and pulls ahead by about 30 percent relative once the rule is larger. Post shift accuracy is a wash (PROBE slightly behind at 3 and 6, slightly ahead at 9), and PROBE has worse recovery speed and more repeated errors at every size.

### Why it matters

This is the first measured, complexity dependent benefit for the explicit belief scaffold, and it matches the hypothesis that structure helps once the state exceeds what the model can track in context. It also localizes the remaining problem precisely: the contradiction driven revision (wipe the belief to unknown, then re explore) is correct but slow, so recovery lags. The value of PROBE is on the learning side, and belief to action or revision is the mechanism to strengthen, the same weak link seen in the Stage 0 ablation (Insight 031).

### Paper relevance

This supports an honest, defensible thesis: explicit rule level belief helps a frozen LLM track rules that are too complex to hold implicitly, with the benefit growing as complexity grows, while the current revision mechanism recovers correctly but slowly. It is a nuanced positive result with a clear boundary and a named next improvement, which is stronger and more credible than an unqualified claim of dominance. Report the crossover table, state the statistical caveat (tens of episodes per cell, consistent trend, wider confidence needs more seeds), and frame revision and belief to action as the identified direction for improvement.

---

## Insight 033: Surgical revision over a structured belief memory beats wipe and re explore, and makes PROBE win both axes

### Observation

Replacing the wipe to unknown revision with a structured belief memory fixed the weak link. The memory holds, per cue, the confirmed key and the set of ruled out keys in the current regime. On a contradiction (a confirmed key later fails) only that cue is reset and its ruled out set restarts at the just failed key; other confirmed cues are untouched. The LLM still selects the action, told to exploit confirmed cues and, for unknown cues, to pick a key not yet ruled out. Result versus baseline, pre shift 0.86/0.52/0.36 versus 0.80/0.38/0.25 at 3/6/9, post shift 0.68/0.46/0.28 versus 0.71/0.39/0.25, recovery 2.3/5.8/11.7 versus 2.3/6.0/5.0. PROBE now wins pre shift at all sizes, wins post shift at 6 and 9 (it lost before), and recovery is on par or better at 3 and 6.

### Why it matters

The gain came from making revision surgical and from remembering ruled out constraints, which lets re exploration deduce (eliminate wrong keys until one remains) instead of guessing from scratch. This is the concrete realization of the Belief Memory and Belief Revision modules for a symbolic rule, and it converts the earlier learning only benefit into a learning and adaptation benefit at moderate to high complexity.

### Paper relevance

Report the before and after of the revision design as evidence that the revision mechanism, not just belief presence, matters: blind wipe and re explore recovered slowly, while surgical revision with a ruled out memory recovered fast and made recovery at least on par with the baseline. The revision fix is a real improvement to the mechanism and should be reported as such.

### Correction from the 50 episode confidence run (Insight 034)

The post shift wins reported above (0.46 at 6 by 6, 0.28 at 9 by 9 beating the baseline) came from a 20 episode run and did NOT survive at 50 episodes. With 95 percent confidence intervals the post shift gaps are about zero and not significant. Do not claim a post shift adaptation win. The surviving, significant claim is the learning (pre shift) benefit. See Insight 034.

---

## Insight 034: With 50 episodes and confidence intervals, the learning benefit is significant and the post shift adaptation benefit is not

### Observation

Rule shift, 50 episodes per cell, mean and 95 percent confidence interval, with a two sample gap CI for baseline versus PROBE. Pre shift (learning): 3 by 3 gap +0.028 [-0.024, +0.081] not significant; 6 by 6 gap +0.137 [+0.071, +0.204] significant; 9 by 9 gap +0.116 [+0.058, +0.173] significant. Post shift (adaptation): 3 by 3 gap +0.045 [+0.011, +0.079] significant but tiny; 6 by 6 gap +0.003 [-0.057, +0.062] not significant; 9 by 9 gap +0.010 [-0.039, +0.059] not significant.

### Why it matters

This is the statistically grounded version of the rule shift result and it supersedes the small sample readings. Explicit rule belief significantly improves learning of complex rules (6 by 6 and 9 by 9), and the effect is absent when the rule is small enough to hold implicitly (3 by 3). The post shift adaptation advantage is not supported: PROBE ties the history based baseline at 6 and 9. A strong frozen LLM re infers a shifted rule from history about as well as the structured agent does, so the value of the belief scaffold is in learning capacity, not in faster re adaptation, at least with this backbone and these settings.

### Paper relevance

Commit to the significant claim only: explicit belief memory significantly improves a frozen LLM's ability to learn complex rules, with the benefit appearing once the rule exceeds what the model tracks implicitly, and with rule shifts handled on par with a strong baseline. Report the full CI table. Frame a post shift adaptation win as future work requiring either a harder adaptation regime or a mechanism that beats history based re inference. This honest scoping is the credible contribution and avoids a claim that would fail replication.

---

## Insight 035: Multi factor rules are where explicit belief most decisively beats a plain LLM

### Observation

On Boss I1, a static rule whose correct key depends on both a color and a shape (built to be non reducible to one feature), 50 episodes with 95 percent CIs: overall accuracy baseline 0.61 versus PROBE 0.88 (gap +0.27), and late asymptotic accuracy baseline 0.67 versus PROBE 0.99 (gap +0.33), both significant. The baseline plateaus near 0.67, the signature of overfitting to a single feature, while PROBE, tracking each color and shape combination explicitly, essentially solves the rule.

### Why it matters

This is the largest and cleanest PROBE advantage measured (bigger than the +0.14 learning gap on rule shift). It isolates the mechanism: a plain LLM reasoning from history tends to latch onto one predictive feature and stops, whereas an explicit per combination belief memory forces the agent to represent the full rule, so it does not collapse to a single factor. Multi factor structure is therefore the regime where the contribution is most visible.

### Paper relevance

Use Boss I1 as the headline demonstration of the contribution: a clean, large, significant win with a clear mechanistic story (no single feature overfit because the belief is per combination). Pair it with the rule shift scaling result (belief helps as complexity grows, shift handled on par) to argue that explicit structured belief helps a frozen LLM whenever the rule is too structured or too large to track implicitly, and that the effect is strongest when the plain model would overfit to one factor.

---

## Insight 036: A consistent internal suite pattern, explicit belief helps in the hard regime and ties a strong baseline at easy asymptotes

### Observation

Across three internal bosses on the same backbone, with 50 episode confidence runs, a consistent shape appears. Boss I1 (multi factor): PROBE beats the baseline by +0.33 asymptotic, a decisive and significant win. Boss I2 (competing hypotheses): PROBE wins the ambiguous phase (+0.14) and overall disambiguation (+0.08), both significant, but ties at the late asymptote. Boss I3 (rule shift): PROBE wins pre shift learning of complex rules (+0.12 to +0.14, significant) and ties on post shift adaptation. In every case the significant PROBE advantage is in the harder part of the task (many factors, ambiguous or early evidence, complex or large rules), and a strong frozen LLM tends to catch up at the easy asymptote.

### Why it matters

This is a coherent, defensible narrative for the paper rather than a scattered set of wins and losses. Explicit structured belief helps a frozen LLM precisely where implicit in context reasoning struggles: when the rule is multi factor (overfit risk), when early evidence is ambiguous (premature commitment risk), or when the rule is large or complex (tracking capacity limit). Where the task is easy enough for the model to solve from history, the scaffold neither helps nor hurts much.

### Paper relevance

Frame the contribution as conditional and mechanistic: explicit belief memory and hypothesis tracking help a frozen LLM in the hard regimes named above, with Boss I1 (multi factor) as the strongest single demonstration, and honest ties at easy asymptotes reported rather than hidden. This conditional framing is both accurate to the data and more credible than a blanket dominance claim.

---

## Insight 037: The complete internal boss suite, six for six, is the paper's core empirical result

### Observation

The full internal suite is done with 50 episode confidence runs and a regression sweep. PROBE significantly beats the history baseline on the primary metric of every boss: I1 multi factor (asymptote +0.33, 0.99 vs 0.67), I2 competing hypotheses (ambiguous +0.14, overall +0.08), I3 rule shift (learning +0.12 to +0.14), I4 probe or progress (reward per step +0.26), I5 relational (early +0.26, overall +0.16, and a persistent asymptote edge reaching 1.00), and I6 mixed multi factor plus shift (pre +0.22, post +0.24, post late +0.29). A regression sweep at small scale confirms 6 of 6 with no regression from the shared code. Ties appear only at the easy asymptotes of the simplest single factor bosses (I2, I3, I4).

### Why it matters

This is a coherent, honest, and statistically supported core result. Explicit structured belief helps a frozen LLM across a spectrum of rule structures, multi factor, ambiguous or confounded, complex or large, relational, and combined novelty, and the advantage is largest exactly where implicit in context reasoning is weakest. Two especially clean cases stand out: relational (I5), where PROBE reaches perfect accuracy and stays ahead even at the asymptote because the belief generalizes the relation while flat history does not; and mixed (I6), where PROBE finally wins post shift adaptation because the shifted rule is complex enough that the baseline cannot re infer it from history, tying together the multi factor benefit (I1) and the revision benefit.

### Paper relevance

Present the six boss suite as the empirical heart of the paper, with a single crossover style table and the conditional framing (explicit belief helps in the hard regime, matches a strong baseline at easy asymptotes). Lead with I1 and I5 as the cleanest demonstrations and I6 as the integrated one. Report the regression sweep as evidence of robustness. External benchmarks, a weaker backbone, and writing remain as breadth and future work, but the internal suite already substantiates the committed contribution.

---

## Insight 038: PROBE's mechanisms are a principled instance of context engineering; use that to frame and ground the paper, not to add a new contribution

### Observation

Current context engineering practice (Anthropic effective context engineering, Manus lessons from building an agent, LangChain context engineering) names exactly the mechanisms PROBE already implements. Structured note taking or external agentic memory corresponds to PROBE's confirmed and ruled out belief memory. Recitation, restating the goal each step to fight lost in the middle, corresponds to PROBE surfacing the belief every step. Preserve failure states so the model can adapt corresponds to PROBE's ruled out set and contradiction signal. Right altitude and structured prompts correspond to PROBE's interface disclosure prompts.

### Why it matters

This is a framing and grounding win, not a new feature. It lets the paper position PROBE within an active, credible line of practice and cite it, describing PROBE as a principled context engineering design specialized for rule level adaptation and revision, rather than an ad hoc scaffold. It also suggests marginal result improvements on the longer or harder tasks (stronger recitation of objective plus belief, history compaction near context limits, cleaner prompt sections), which are hygiene and would not move the internal suite that is already near ceiling.

### Paper relevance

Cite Anthropic and Manus (and LangChain) in related work and method to ground PROBE's belief loop in context engineering. Keep the contribution the same, rule level belief plus contradiction driven revision; context engineering is the field the method sits in and its implementation discipline, not the headline. Explicitly exclude weight or vector compression such as TurboQuant from the contribution; it is serving efficiency, orthogonal to the thesis, and at most a single related work sentence under efficiency (consistent with Insight 026 on not making compression the contribution).

---

## Insight 039: Position PROBE as an explicit, inspectable, in context world model of the rules, against trained world models and skill growers

### Observation

The agentic world models and generalist agents line is the broad field PROBE sits in. Three reference points, separated by whether they train and what they model. Gato (DeepMind) trains one transformer over tokenized states across embodiments. Qwen-AgentWorld trains a language world model, treating environment modeling as a training objective. Alita uses a mostly frozen LLM but self evolves external tools and protocols (MCPs), a Voyager style capability grower, achieving strong GAIA results; it does not track rule beliefs or do contradiction driven revision. These join the existing neighbors Voyager (grows code skills) and Align While Search (estimates object locations in a static world).

### Why it matters

The separation is clean and favorable. Everyone else either trains a model (Gato, Qwen-AgentWorld) or grows capabilities (Voyager, Alita), and AWS estimates state in a static world. PROBE trains nothing and models the environment RULES explicitly, revising them by contradiction under non stationary conditions, with an inspectable trace. The useful vocabulary lift is world model: PROBE's rule belief is a lightweight, explicit, in context world model of the rules, as opposed to a learned neural world model or a skill or tool repertoire.

### Paper relevance

Position PROBE as an explicit, inspectable, frozen LLM world model of the environment rules, maintained and revised in context without training. Extend the comparison table with Gato, Qwen-AgentWorld, and Alita along the two axes trains or not and models rules versus state versus skills. This is framing and citations, not new features; do not build world model training or tool synthesis. Recurring discipline note: several enhancement ideas have arrived (token saving, context engineering, world models); each is cite and frame, not rebuild, and the committed contribution and the locked, validated design stay fixed. With strong results in hand, the priority is finishing the external run and writing, not adding axes.

---

## Insight 040: The advantage survives a stronger baseline and a weaker backbone

### Observation

Two follow up runs on the multi factor boss (I1) probed the two obvious objections to the headline result. First, a ReAct style baseline was added on the same 70B backbone: it reasons before acting and keeps a scratchpad of its own thoughts, but holds no structured belief and no contradiction detector. On asymptotic accuracy the plain baseline reached 0.669, ReAct reached 0.846, and PROBE reached 0.994; PROBE beats ReAct by +0.148 [0.100, 0.195] and ReAct beats plain history by +0.177 [0.105, 0.250]. Second, the plain baseline and PROBE were rerun on meta-llama/llama-3.1-8b-instruct, an order of magnitude smaller: the baseline fell to 0.411 overall while PROBE held 0.684, a gap of +0.273 [0.226, 0.320], about the same absolute size as the +0.268 gap on the 70B model.

### Why it matters

Both are the objections a reviewer raises first. The ReAct result shows the win is not merely from surfacing a reasoning trace, since ReAct already supplies that and still loses to PROBE by a significant margin; the structured belief and its revision carry the remaining gap. The weaker backbone result shows the win is not an artifact of a strong model, since the loop delivers a gain of the same absolute size on a much smaller model and rescues most of the accuracy the small model loses on its own. This is exactly the pattern a scaffold that supplies missing structure should show.

### Paper relevance

Reported as a new subsection (Stronger Baseline and Weaker Backbone) with a table, and reflected in the abstract, the single backbone paragraph, and the limitations. The frontier gpt-4.1 confirmation remains the one open backbone check. Discipline note: these are confirmations of the committed contribution on the existing boss, not new axes; the locked design and the contribution are unchanged.
