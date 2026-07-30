#!/usr/bin/env bash
# TextWorld hidden-rule run, parallel across seed chunks.
# tatsu's parser is NOT thread-safe (shared global _PARSER), so each worker
# runs workers=1; parallelism comes from many separate PROCESSES over disjoint
# seed subsets, the same pattern as run_mh_chunked.sh for NLE.
set -a
. .env 2>/dev/null
set +a

MODEL="${OPENROUTER_MODELS:-meta-llama/llama-3.3-70b-instruct}"
MAXTOK="${OPENROUTER_MAX_TOKENS:-512}"
BUDGET="${TW_BUDGET:-30}"
QUEST="${TW_QUEST:-4}"
ROOMS="${TW_ROOMS:-4}"
OBJECTS="${TW_OBJECTS:-6}"
CHUNK="${TW_CHUNK:-25}"
LAST="${TW_LAST:-99}"
VARIANTS="${TW_VARIANTS:-baseline_tw reflexion_tw probe_tw}"

for V in $VARIANTS; do
  START=0
  while [ "$START" -le "$LAST" ]; do
    END=$((START + CHUNK - 1))
    [ "$END" -gt "$LAST" ] && END="$LAST"
    SEEDS=$(seq -s, "$START" "$END")
    OPENROUTER_MODELS="$MODEL" OPENROUTER_MAX_TOKENS="$MAXTOK" \
      TEXTWORLD_SEEDS="$SEEDS" TEXTWORLD_VARIANTS="$V" \
      TEXTWORLD_BUDGET="$BUDGET" TEXTWORLD_QUEST="$QUEST" \
      TEXTWORLD_ROOMS="$ROOMS" TEXTWORLD_OBJECTS="$OBJECTS" \
      TEXTWORLD_MAX_WORKERS=1 TEXTWORLD_BATCH_ID="twc_${V}_${START}" \
      PYTHONPATH=src python3 -u scripts/run_textworld.py > "twc_${V}_${START}.log" 2>&1 &
    sleep 3
    START=$((START + CHUNK))
  done
done

echo "launched $(jobs -p | wc -l) worker processes"
wait
echo "==== ALL CHUNKS DONE ===="
for V in $VARIANTS; do
  n=$(cat twc_${V}_*.log 2>/dev/null | grep -c "\[$V\] seed")
  w=$(cat twc_${V}_*.log 2>/dev/null | grep "\[$V\] seed" | grep -c "won=True")
  echo "$V: solved ${w}/${n}"
done
