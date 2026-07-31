# Running the MiniHack boss in a Linux Codespace

MiniHack (NetHack via `nle`) does not run on the macOS + Python 3.13 + NumPy 2 setup: the unmaintained `gym` library breaks on NumPy 2, so no environment registers. On Linux with NumPy pinned below 2 it works. Run this boss in a GitHub Codespace, bring the traces back, and the paper integration happens on the main machine.

## Steps

1. Open this repository in a Codespace (Code, Codespaces, Create codespace on main). Codespaces run Ubuntu.

2. System build dependencies for `nle` (only needed if pip builds it from source):

   ```
   sudo apt-get update
   sudo apt-get install -y build-essential autoconf libtool pkg-config flex bison libbz2-dev cmake
   ```

3. A clean Python environment with the pinned versions:

   ```
   python3.11 -m venv .venv-mh || python3 -m venv .venv-mh
   .venv-mh/bin/pip install --upgrade pip
   .venv-mh/bin/pip install -r requirements-minihack.txt
   ```

4. Confirm MiniHack actually registers environments:

   ```
   .venv-mh/bin/python -c "import warnings; warnings.filterwarnings('ignore'); import gymnasium as g, minihack; print('envs:', len([e for e in g.envs.registry if 'MiniHack' in e]))"
   ```

   Expect a nonzero count (about 161). MiniHack registers into gymnasium, not classic gym. If it prints 0, stop and report the output.

5. Set the OpenRouter key (do not commit it):

   ```
   export OPENROUTER_API_KEY=sk-or-...your-key...
   ```

6. Run the boss (baseline and PROBE, 10 seeds, MazeWalk 9x9):

   ```
   OPENROUTER_MODELS=meta-llama/llama-3.3-70b-instruct OPENROUTER_MAX_TOKENS=512 \
   MINIHACK_ENV=MiniHack-MazeWalk-9x9-v0 MINIHACK_SEEDS=0,1,2,3,4,5,6,7,8,9 \
   MINIHACK_BUDGET=50 MINIHACK_VARIANTS=baseline_mh,probe_mh MINIHACK_BATCH_ID=mh1 \
   PYTHONPATH=src .venv-mh/bin/python scripts/run_minihack.py
   ```

   Other env ideas: `MiniHack-Room-Random-15x15-v0`, `MiniHack-Corridor-R2-v0`.

7. Bring the traces back (they are gitignored, so force add):

   ```
   git add -f traces/minihack_*_mh1.csv outputs/minihack_summary_*_mh1.json
   git commit -m "minihack boss traces from codespace run"
   git push
   ```

   Then the main machine pulls and computes the confidence intervals and folds the result into the paper.

## Notes

- `nle` is not thread safe, so the runner is serial by design.
- Success is defined as reaching the goal (a positive step reward) within the budget.
- MazeWalk and NetHack navigation are hard for a text agent, so absolute success rates may be low. That is an honest stress-test data point, not necessarily a win.
