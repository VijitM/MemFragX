#!/usr/bin/env python3
"""
Safer replay_compact.py
Usage:
  python3 tools/replay_compact.py <mftrace_log.csv> <out_replay.c> [--max-objects N] [--max-per-obj BYTES]

Produces a non-blocking replay C program that allocates a bounded number of objects,
touches pages to materialize them, waits a small sleep for snapshots, then frees and exits.
"""
import csv, sys, os

if len(sys.argv) < 3:
    print("Usage: python3 tools/replay_compact.py <mftrace_log.csv> <out_replay.c> [--max-objects N] [--max-per-obj BYTES]")
    sys.exit(1)

trace_path = sys.argv[1]
out_path = sys.argv[2]

# defaults
max_objects = 5000
max_per_obj = 16 * 1024 * 1024  # 16 MB

# parse flags
for i,arg in enumerate(sys.argv[3:], start=3):
    if arg == "--max-objects" and i+1 < len(sys.argv):
        max_objects = int(sys.argv[i+1])
    if arg == "--max-per-obj" and i+1 < len(sys.argv):
        max_per_obj = int(sys.argv[i+1])

if not os.path.exists(trace_path):
    print("Trace file not found:", trace_path); sys.exit(1)

# read trace and compute final live allocations (ptr->size)
allocs = {}
with open(trace_path, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if not row: continue
        op = (row.get('event') or row.get('op') or "").strip().upper()
        ptr = row.get('ptr') or "0x0"
        size = row.get('size') or "0"
        try:
            size = int(size) if size else 0
        except:
            size = 0
        if op in ("ALLOC", "CALLOC", "REALLOC", "POSIX_MEMALIGN"):
            allocs[ptr] = size
        elif op == "FREE":
            if ptr in allocs: del allocs[ptr]

sizes = [s for s in allocs.values() if s > 0]
sizes.sort(reverse=True)  # largest first

# bounds
sizes = [min(s, max_per_obj) for s in sizes][:max_objects]

# write C replay program
with open(out_path, "w") as out:
    out.write("/* Auto-generated safe replay program */\n")
    out.write("#include <stdlib.h>\n#include <stdio.h>\n#include <unistd.h>\n#include <string.h>\n#include <stdint.h>\n#include <time.h>\n\nint main() {\n")
    out.write("    size_t n = %d;\n" % len(sizes))
    out.write("    void **arr = malloc(n * sizeof(void*));\n")
    out.write("    if (!arr) { perror(\"malloc\"); return 1; }\n")
    out.write("    size_t i = 0;\n")
    for s in sizes:
        touch = 4096 if s >= 4096 else s
        out.write(f"    arr[i] = malloc({s}); if (!arr[i]) {{ perror(\"malloc\"); return 1; }};\n")
        out.write(f"    memset(arr[i], 0xAB, {touch});\n")
        out.write("    i++;\n")
    out.write('    printf("[replay] Allocated %zu objects, holding for 3s\\n", (size_t)i);\n')
    out.write("    fflush(stdout);\n")
    out.write("    struct timespec ts = {8,0}; nanosleep(&ts, NULL);\n")
    out.write("    for (size_t j=0;j<i;j++) { free(arr[j]); }\n")
    out.write("    free(arr);\n")
    out.write('    printf("[replay] Freed and exiting\\n"); fflush(stdout);\n')
    out.write("    return 0;\n}\n")

print("Wrote safe replay to", out_path, " (objects:", len(sizes), ")")

