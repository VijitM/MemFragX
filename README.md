# MemFragX (extended)
This repository contains an improved prototype for heap fragmentation tracing, Approach A (malloc_trim) and Approach B (replay compaction), and analysis tools.

Build:
```
make all
```

Run Approach A demo:
```
chmod +x run_all_trim_experiment.sh
./run_all_trim_experiment.sh
```

Generate replay compaction program after a trace:
```
python3 tools/replay_compact.py results/mftrace_log.csv replay_compact.c
gcc -O2 -o replay_compact replay_compact.c
./replay_compact
```

Analysis:
```
python3 analysis/analysis.py results/mftrace_log.csv results/smaps
```
