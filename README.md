# MemFragX — Memory Fragmentation Analysis Framework

**MemFragX** is a modular framework for **analyzing heap memory fragmentation** in real-world programs.  
It dynamically intercepts memory allocation functions, records allocation traces, generates reproducible replays, and compares the impact of defragmentation strategies.

---

## 🚀 Features

- **Dynamic memory tracing** via `LD_PRELOAD`  
- **Detailed allocation logging** (`malloc`, `calloc`, `realloc`, `free`) with timestamps and thread IDs  
- **Reproducible replay generation** (Approach B — restart-and-replay / compact replay)  
- **Defragmentation analysis** (live `malloc_trim()` Approach A and replay Approach B)  
- **Heatmaps and impact graphs** for visual insight  
- Works with **any dynamically linked program** — no source-code changes required

---

## Repository layout

```
MemFragX/
├── tracer/                  # LD_PRELOAD shared library (libmftrace.so)
│   └── tracer.c
├── tools/
│   ├── trace_any.py         # Universal wrapper (trace + replay + compare)
│   ├── replay_compact.py    # Safe replay generator
│   ├── metrics_viz.py       # Visualization: heatmaps, workload graphs
│   └── snapshotter.py       # simple /proc/<pid>/smaps snapshotter
├── analysis/
│   └── analysis.py          # Core analysis of A vs B results
├── workload/                # Optional synthetic test workload
├── results/                 # Output folder for traces, smaps, plots (created at runtime)
└── README.md
```

---

## Prerequisites

- Linux (dynamically linked binaries, glibc)  
- GCC or Clang  
- Python 3.8+ with packages:
  ```bash
  pip install pandas matplotlib numpy
  ```

---

## Build the tracer

Compile the memory tracer (produce `tracer/libmftrace.so`):

```bash
cd tracer
gcc -O2 -fPIC -shared -ldl -pthread -o libmftrace.so tracer.c
cd ..
```

---

## Quick usage (trace any program)

The simplest end-to-end command uses the wrapper to trace a program, capture smaps, analyze, generate and run a replay, and produce comparisons:

```bash
python3 tools/trace_any.py --program "./my_program arg1 arg2" --out results/my_program_run
```

This will:
1. Run your program under `libmftrace.so` with `MFTRACE_LOG` set to `results/.../mftrace_log.csv`.  
2. Capture `/proc/<pid>/smaps` mid-run into `results/.../smaps`.  
3. Run `analysis/analysis.py` to compute basic metrics and write `summary.json`.  
4. Generate `replay.c` via `tools/replay_compact.py`, compile and run it (Approach B).  
5. Capture `smaps` for the replay and run comparison analysis.  
6. Produce visual outputs (heatmaps, RSS comparison) inside the results folder.

---

## Outputs and where to find them

Each run stores outputs under the `--out` directory you specify. Common files:

- `mftrace_log.csv` — allocation/free trace with `ts_ns,event,ptr,size,tid`  
- `smaps` — `/proc/<pid>/smaps` snapshot of the traced run  
- `replay.c`, `replay` — generated replay source and binary for Approach B  
- `smaps_replay` — `/proc/<pid>/smaps` of the replay run  
- `summary.json` — numeric summary of allocations/frees, total bytes, threads  
- `heatmap_allocations.png` — thread × size allocation heatmap  
- `impact_memory_usage.png` — cumulative/net allocated MB vs time  
- `rss_comparison.png` — Approach A vs B RSS plot

---

## Example test programs

### 1) Simple C allocator test (recommended)
Create `malloc_test.c`:
```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main() {
    void *blocks[5];
    for (int i = 0; i < 5; i++) {
        size_t sz = (i + 1) * 1024 * 1024; // 1MB, 2MB, ...
        blocks[i] = malloc(sz);
        memset(blocks[i], 0xAA, sz);
        usleep(500000);
    }
    for (int i = 0; i < 5; i += 2) free(blocks[i]);
    sleep(2);
    return 0;
}
```
Compile and run:
```bash
gcc -O2 malloc_test.c -o malloc_test
python3 tools/trace_any.py --program "./malloc_test" --out results/malloc_test
```

### 2) Python memory stress (no compile)
```bash
python3 tools/trace_any.py --program "python3 -c 'a=[b\"x\"*1024 for _ in range(500000)]; del a'" --out results/python_run
```

### 3) Quick real-world smoke test
```bash
python3 tools/trace_any.py --program "curl -s https://example.com" --out results/curl_run
```

---

## Running only parts of the pipeline

- Trace only (no replay): set `--no-replay` to skip Approach B.
- Capture smaps manually:
  ```bash
  LD_PRELOAD=tracer/libmftrace.so MFTRACE_LOG=results/tmp.csv ./myprog &
  PID=$!
  sleep 2
  cat /proc/$PID/smaps > results/tmp_smaps
  wait $PID
  ```
- Run analysis only:
  ```bash
  env -u LD_PRELOAD python3 analysis/analysis.py results/.../mftrace_log.csv results/.../smaps
  ```
- Generate metrics visualizations manually:
  ```bash
  python3 tools/metrics_viz.py results/.../mftrace_log.csv results/.../smaps results/.../smaps_replay
  ```

---

## Notes, caveats, and tips

- `LD_PRELOAD` works only with dynamically linked binaries. Static binaries ignore `LD_PRELOAD`.  
- Some programs use alternate allocators (jemalloc, tcmalloc); those may bypass `malloc/free` hooks. You can still instrument them by preloading compatible hooks or using their APIs if available.  
- Tracing adds overhead; run multiple trials for performance-sensitive comparisons.  
- The tracer writes logs to the path in `MFTRACE_LOG`. Use `trace_any.py` so the log is placed inside the run output folder.  
- The replay generator supports safe bounds (max objects, per-object caps) to avoid OOMs; tune flags in `replay_compact.py` if needed.

---

## Extending MemFragX

- Add new defragmentation strategies (in-place compaction, OS-level hints) and compare with Approach A/B.  
- Simulate multithreaded replay: extend `replay_compact.py` to generate `pthread`-based replays based on `tid` groups.  
- Integrate per-page heatmaps and fragmentation ratio computations.  
- Use cgroups/ulimits to safely run large replays in CI.

---

## License & attribution

MIT License — (c) 2025 Vijit Mann and contributors
