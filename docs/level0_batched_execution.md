# Level 0 Batched Execution Plan

This file defines how the Level 0 external plain-LLM benchmark can be run in small chunks without changing the underlying protocol target.

## Full Protocol Target

- Benchmark: `MiniGrid-GoToObject-6x6-N2-v0`
- Seeds: `10`
- Episodes per seed: `20`

## Why batching is being used

The LLM-backed MiniGrid baseline is interactive and requires repeated model calls.

Batching lets us:

- reduce run fragility
- manage runtime
- resume partial progress
- preserve the full target protocol

## Initial Batch Plan

- `2` seeds per batch
- `2` episodes per seed

That means each batch covers:

- `4` episodes

## Example Batches

- Batch 1:
  - seeds `0,1`
  - episodes `0,1`
- Batch 2:
  - seeds `0,1`
  - episodes `2,3`
- Batch 3:
  - seeds `2,3`
  - episodes `0,1`

Continue until the full seed/episode coverage is complete.

## Aggregation Rule

The final Level 0 result should:

- merge all batch traces
- merge all batch summaries
- compute metrics over all completed planned coverage
- never drop failed or slow batches from the final report

## Constraint

Batching changes execution, not evaluation logic.
