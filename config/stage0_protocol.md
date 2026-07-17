# Stage 0 Protocol

- External boss: `MiniGrid-GoToObject-6x6-N2-v0`
- Seeds: `10`
- Evaluation episodes per seed: `20`
- Locked baseline variants:
  - `random_policy`
  - `plain_llm_agent`

First implementation milestone:

- `BossI0`
- trace logger
- `random_policy`
- evaluation runner
- summary output

## Batched Execution Rule

For LLM-backed interactive runs, the Stage 0 protocol may be executed in fixed batches and aggregated later.

This is allowed only if:

- the full protocol target remains unchanged
- the batch plan is defined before the full run
- all batch outputs are retained
- aggregation includes all executed batches honestly

### Current Batch Plan

- Full target:
  - `10` seeds
  - `20` episodes per seed
- Initial LLM batch size:
  - `2` seeds per batch
  - `2` episodes per seed

### Required Batch Metadata

- batch_id
- backend
- seed_range
- episode_range
- trace_file
- summary_file
