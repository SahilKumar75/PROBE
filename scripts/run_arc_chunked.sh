#!/usr/bin/env bash
# ARC-AGI-3 boss, parallel across seed chunks with single-worker processes.
# Mirrors run_tw_chunked.sh: the SDK/engine is safest driven serially per
# process, so parallelism comes from many processes over disjoint seed subsets.
set -a
. .env 2>/dev/null
set +a
mkdir -p runlogs

MODEL="${OPENROUTER_MODELS:-meta-llama/llama-3.3-70b-instruct}"
MAXTOK="${OPENROUTER_MAX_TOKENS:-512}"
BUDGET="${ARC_BUDGET:-40}"
GAMES="${ARC_GAMES:-simple_maze,merge,complex_maze}"
CHUNK="${ARC_CHUNK:-25}"
LAST="${ARC_LAST:-99}"
VARIANTS="${ARC_VARIANTS:-baseline_arc reflexion_arc probe_arc}"

for V in $VARIANTS; do
  START=0
  while [ "$START" -le "$LAST" ]; do
    END=$((START + CHUNK - 1))
    [ "$END" -gt "$LAST" ] && END="$LAST"
    SEEDS=$(seq -s, "$START" "$END")
    OPENROUTER_MODELS="$MODEL" OPENROUTER_MAX_TOKENS="$MAXTOK" \
      ARC_GAMES="$GAMES" ARC_SEEDS="$SEEDS" ARC_VARIANTS="$V" \
      ARC_BUDGET="$BUDGET" ARC_MAX_WORKERS=1 ARC_BATCH_ID="arcc_${V}_${START}" \
      PYTHONPATH=src python3 -u scripts/run_arc.py > "runlogs/arcc_${V}_${START}.log" 2>&1 &
    sleep 3
    START=$((START + CHUNK))
  done
done

echo "launched $(jobs -p | wc -l) worker processes"
wait
echo "==== ALL CHUNKS DONE ===="
for V in $VARIANTS; do
  n=$(cat runlogs/arcc_${V}_*.log 2>/dev/null | grep -c " seed ")
  w=$(cat runlogs/arcc_${V}_*.log 2>/dev/null | grep " seed " | grep -c "won=True")
  echo "$V: solved ${w}/${n}"
done
