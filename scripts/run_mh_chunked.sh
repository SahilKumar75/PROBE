#!/usr/bin/env bash
set -a
. .env 2>/dev/null
set +a
mkdir -p runlogs

ENV="MiniHack-River-Narrow-v0"
BUDGET="${MH_BUDGET:-120}"
CHUNK="${MH_CHUNK:-10}"
LAST="${MH_LAST:-49}"
VARIANTS="${MH_VARIANTS:-reflexion_mh probe_mh}"

for V in $VARIANTS; do
  START=0
  while [ "$START" -le "$LAST" ]; do
    END=$((START + CHUNK - 1))
    [ "$END" -gt "$LAST" ] && END="$LAST"
    SEEDS=$(seq -s, "$START" "$END")
    MINIHACK_ENV="$ENV" MINIHACK_SEEDS="$SEEDS" MINIHACK_VARIANTS="$V" \
      MINIHACK_BUDGET="$BUDGET" MINIHACK_MAX_WORKERS=1 \
      MINIHACK_BATCH_ID="mhc_${V}_${START}" \
      python -u scripts/run_minihack.py > "runlogs/mhc_${V}_${START}.log" 2>&1 &
    sleep 3
    START=$((START + CHUNK))
  done
done

echo "launched $(jobs -p | wc -l) worker processes"
wait
echo "==== ALL CHUNKS DONE ===="
for V in $VARIANTS; do
  n=$(cat runlogs/mhc_${V}_*.log 2>/dev/null | grep -c "success=")
  s=$(cat runlogs/mhc_${V}_*.log 2>/dev/null | grep -oE "success=[01]" | grep -c "success=1")
  echo "$V: solved ${s}/${n}"
done
