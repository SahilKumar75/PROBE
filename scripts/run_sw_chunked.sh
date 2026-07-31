#!/usr/bin/env bash
# ScienceWorld boss, parallel across (variant, task) pairs.
# One JVM per process (py4j is not thread-safe), serial inside a process,
# the same pattern as the TextWorld/MiniHack/ARC launchers.
set -a
. .env 2>/dev/null
set +a
mkdir -p runlogs

MODEL="${OPENROUTER_MODELS:-meta-llama/llama-3.3-70b-instruct}"
MAXTOK="${OPENROUTER_MAX_TOKENS:-512}"
BUDGET="${SW_BUDGET:-35}"
TASKS="${SW_TASKS:-chemistry-mix change-the-state-of-matter-of}"
VARS="${SW_VARS:-}"
VARIANTS="${SW_VARIANTS:-baseline_sw reflexion_sw probe_sw probe52_sw}"

for V in $VARIANTS; do
  for T in $TASKS; do
    OPENROUTER_MODELS="$MODEL" OPENROUTER_MAX_TOKENS="$MAXTOK" \
      SW_TASKS="$T" SW_VARS="$VARS" SW_VARIANTS="$V" \
      SW_BUDGET="$BUDGET" SW_BATCH_ID="swc_${V}_${T}" \
      PYTHONPATH=src python3 -u scripts/run_scienceworld.py > "runlogs/swc_${V}_${T}.log" 2>&1 &
    sleep 4
  done
done

echo "launched $(jobs -p | wc -l) worker processes"
wait
echo "==== ALL CHUNKS DONE ===="
for V in $VARIANTS; do
  best=$(cat runlogs/swc_${V}_*.log 2>/dev/null | grep -oE "best [0-9]+" | awk '{s+=$2; n+=1} END {if(n>0) printf "%.1f over %d eps", s/n, n; else print "no data"}')
  echo "$V: mean best score $best"
done
