#!/usr/bin/env bash
# MemFragX Full Experiment (Approach A + B)

set -euo pipefail
ROOT="$(pwd)"
RESULTS="$ROOT/results"
mkdir -p "$RESULTS"

stop_snapshotter() {
    if env -u LD_PRELOAD ps -p "$S_PID" >/dev/null 2>&1; then
        kill "$S_PID" 2>/dev/null || true
    fi
}

echo "[*] Building project..."
make all

# Approach A: Live malloc_trim

echo "[A] Running Approach A (live trim)..."
mkdir -p "$RESULTS/A/smaps"
export MFTRACE_LOG="$RESULTS/A/mftrace_log.csv"
#export LD_PRELOAD="$ROOT/tracer/libmftrace.so:$ROOT/tools/trim_handler.so"

LD_PRELOAD="$ROOT/tracer/libmftrace.so:$ROOT/tools/trim_handler.so" \
  ./workload/workload uniform 200000 4096 >"$RESULTS/A/workload.out" 2>"$RESULTS/A/workload.err" &
W_PID=$!

echo "    Workload PID = $W_PID"

echo "[A] Starting snapshotter..."
env -u LD_PRELOAD python3 "$ROOT/tools/snapshotter.py" "$W_PID" "$RESULTS/A/smaps" 1 >"$RESULTS/A/snap.log" 2>&1 &
S_PID=$!

echo "[A] Waiting until workload has active memory usage..."
for i in {1..20}; do
    if ! env -u LD_PRELOAD ps -p "$W_PID" >/dev/null 2>&1; then
        echo "[!] Workload ended before trim could be triggered."
        break
    fi
    vmrss=$(grep -i VmRSS /proc/$W_PID/status | awk '{print $2}')
    if [ "${vmrss:-0}" -gt 20000 ]; then  # about 20 MB threshold
        echo "    Detected active memory usage: ${vmrss} kB"
        echo "[A] Triggering malloc_trim() now..."
        bash "$ROOT/tools/mf_trim_helper.sh" "$W_PID" || echo "[!] Trim trigger failed"
        break
    fi
    sleep 1
done


wait "$W_PID" || true
stop_snapshotter

echo "[A] Analyzing results..."
env -u LD_PRELOAD python3 "$ROOT/analysis/analysis.py" "$RESULTS/A/mftrace_log.csv" "$RESULTS/A/smaps" || true

echo "[✓] Approach A complete."


# Approach B: Restart-and-Compact Replay

echo "[B] Running Approach B (restart replay)..."
mkdir -p "$RESULTS/B"

# Generate replay source using tracer log from A
env -u LD_PRELOAD python3 "$ROOT/tools/replay_compact.py" "$RESULTS/A/mftrace_log.csv" "$RESULTS/B/replay.c"

gcc -O2 "$RESULTS/B/replay.c" -o "$RESULTS/B/replay"
"$RESULTS/B/replay" >"$RESULTS/B/replay.out" 2>"$RESULTS/B/replay.err"

# Run analysis on replay phase (no smaps, only allocations)
env -u LD_PRELOAD python3 "$ROOT/analysis/analysis.py" "$RESULTS/A/mftrace_log.csv" "$RESULTS/A/smaps" || true

echo "[✓] Approach B complete."

# Comparison Plot (RSS A vs B)

echo "[*] Generating comparison plot..."

python3 - <<'PYCODE'
import os, pandas as pd, matplotlib.pyplot as plt

root = "results"
a_dir = os.path.join(root, "A")
b_dir = os.path.join(root, "B")
plot_path = os.path.join(root, "rss_comparison.png")

def get_rss_series(smaps_dir):
    rss = []
    times = []
    files = sorted([f for f in os.listdir(smaps_dir) if f.startswith("smap_")])
    for i, fname in enumerate(files):
        with open(os.path.join(smaps_dir, fname)) as f:
            total_rss = 0
            for line in f:
                if line.startswith("Rss:"):
                    total_rss += int(line.split()[1])
            rss.append(total_rss)
            times.append(i)
    return pd.Series(rss, index=times)

rss_a = get_rss_series(os.path.join(a_dir, "smaps")) if os.path.exists(os.path.join(a_dir, "smaps")) else None
rss_b = get_rss_series(os.path.join(b_dir, "smaps")) if os.path.exists(os.path.join(b_dir, "smaps")) else None

plt.figure(figsize=(8,5))
if rss_a is not None:
    plt.plot(rss_a.index, rss_a.values, label="Approach A (Live Trim)", linewidth=2)
if rss_b is not None:
    plt.plot(rss_b.index, rss_b.values, label="Approach B (Replay Compact)", linewidth=2, linestyle="--")
plt.xlabel("Snapshot Index")
plt.ylabel("Total RSS (kB)")
plt.title("Memory Usage Comparison: Approach A vs B")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig(plot_path)
print(f"[+] Comparison plot saved to {plot_path}")
PYCODE

echo
echo "[✅] Full experiment complete!"
echo "Results:"
echo "  • Approach A → $RESULTS/A/"
echo "  • Approach B → $RESULTS/B/"
echo "  • Comparison Plot → $RESULTS/rss_comparison.png"
echo

#Test for Delimiter (ignore)

python3 - <<'EOF'
import csv
path = "results/A/mftrace_log.csv"
with open(path, newline="") as f:
    sample = f.read(1024)
    f.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    reader = csv.DictReader(f, dialect=dialect)
    print("Detected delimiter:", repr(dialect.delimiter))
    print("Header fields:", reader.fieldnames)
EOF

