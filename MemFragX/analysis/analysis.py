#!/usr/bin/env python3
import csv
import sys
import os
from collections import defaultdict

"""
analysis.py — analyzes mftrace_log.csv and smaps snapshots.
Usage:
    python3 analysis.py <mftrace_log.csv> <smaps_folder>

Outputs:
    Basic statistics and (optionally) a summary.json in the same folder.
"""

if len(sys.argv) < 3:
    print("Usage: python3 analysis.py <mftrace_log.csv> <smaps_folder>")
    sys.exit(1)

csv_path = sys.argv[1]
smaps_folder = sys.argv[2]

if not os.path.exists(csv_path):
    print(f"[!] Trace file not found: {csv_path}")
    sys.exit(1)

# --- Read CSV safely ---
import csv

records = []
with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
    sample = f.read(1024)
    f.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    reader = csv.DictReader(f, dialect=dialect)

    print("Detected delimiter:", repr(dialect.delimiter))
    print("Detected fields:", reader.fieldnames)

    for row in reader:
        if not row:
            continue

        normalized = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}

        ts = normalized.get("ts_ns") or normalized.get("timestamp") or "0"
        event = normalized.get("event") or normalized.get("op") or "UNKNOWN"
        ptr = normalized.get("ptr") or ""
        size = normalized.get("size") or normalized.get("bytes") or "0"
        tid = normalized.get("tid") or normalized.get("thread") or "0"

        try:
            ts_ns = int(ts) if ts.isdigit() else 0
            size = int(size) if size.isdigit() else 0
            tid = int(tid) if tid.isdigit() else 0
        except ValueError:
            continue

        records.append({
            "ts_ns": ts_ns,
            "event": event.upper(),
            "ptr": ptr,
            "size": size,
            "tid": tid
        })

print(f"[✓] Parsed {len(records)} trace entries from {csv_path}")
if records:
    print("Sample record:", records[0])
    print("Unique events found:", set(r["event"] for r in records))

print(f"[✓] Parsed {len(records)} trace entries from {csv_path}")
if records:
    print("Sample parsed record:", records[0])
    print("Unique events found:", set(r['event'] for r in records))
else:
    print("[!] No records parsed — check delimiter or field names")


# --- Basic statistics ---
allocs = sum(1 for r in records if r['event'] in ('ALLOC', 'CALLOC', 'REALLOC'))
frees  = sum(1 for r in records if r['event'] == 'FREE')
unique_threads = len(set(r['tid'] for r in records))
total_alloc = sum(r['size'] for r in records if r['event'] in ('ALLOC', 'CALLOC', 'REALLOC'))
net_alloc = total_alloc - sum(r['size'] for r in records if r['event'] == 'FREE')

print("\n--- Memory Trace Summary ---")
print(f"Total allocations : {allocs}")
print(f"Total frees       : {frees}")
print(f"Threads involved  : {unique_threads}")
print(f"Total alloc bytes : {total_alloc}")
print(f"Net alloc bytes   : {net_alloc}")
print("-----------------------------")

# --- Optional: read smaps snapshots for memory footprint estimation ---
def estimate_smaps_memory(smaps_dir):
    total = 0
    for root, _, files in os.walk(smaps_dir):
        for file in files:
            if not file.endswith(".txt"):
                continue
            try:
                with open(os.path.join(root, file)) as sf:
                    for line in sf:
                        if line.startswith("Rss:"):
                            parts = line.split()
                            total += int(parts[1])  # kB
            except Exception:
                continue
    return total

if os.path.exists(smaps_folder):
    rss_kb = estimate_smaps_memory(smaps_folder)
    print(f"Approx. total RSS from smaps: {rss_kb} KB")
else:
    print(f"[!] smaps folder not found: {smaps_folder}")

# --- Optional JSON summary ---
summary = {
    "trace_file": os.path.basename(csv_path),
    "records": len(records),
    "allocs": allocs,
    "frees": frees,
    "threads": unique_threads,
    "total_alloc_bytes": total_alloc,
    "net_alloc_bytes": net_alloc,
}

import json
summary_path = os.path.join(os.path.dirname(csv_path), "summary.json")
with open(summary_path, "w") as jf:
    json.dump(summary, jf, indent=4)
print(f"[✓] Summary saved to {summary_path}")

