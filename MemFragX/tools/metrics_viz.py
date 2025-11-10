#!/usr/bin/env python3
"""
metrics_viz.py — Generate memory allocation heatmaps and workload impact graphs
Usage: python3 tools/metrics_viz.py <mftrace_log.csv> [smapsA] [smapsB]
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

def load_trace(path):
    df = pd.read_csv(path)
    # Normalize
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ['ts_ns', 'size', 'tid']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    df = df[df['event'].isin(['ALLOC','FREE','REALLOC'])]
    return df

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_gantt_from_trace(trace_csv, out_dir=None):
    if isinstance(trace_csv, pd.DataFrame):
        df = trace_csv
        trace_path = getattr(df, "name", "trace")  # for labeling
    else:
        trace_path = trace_csv
        df = pd.read_csv(trace_csv)

    # Determine save directory
    if out_dir is None:
        # Default to same folder as the trace file
        out_dir = os.path.dirname(os.path.abspath(trace_path))
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, "gantt_chart.png")

    # ↓ the rest of your existing plotting code ↓
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[df['event'].isin(['ALLOC', 'FREE'])]
    df['ts_ns'] = pd.to_numeric(df['ts_ns'], errors='coerce')
    df['size'] = pd.to_numeric(df['size'], errors='coerce').fillna(0)

    allocs = {}
    records = []

    for _, row in df.iterrows():
        ptr = row['ptr']
        ts = row['ts_ns'] / 1e6  # convert ns→ms
        tid = int(row['tid'])
        if row['event'] == 'ALLOC':
            allocs[ptr] = (ts, row['size'], tid)
        elif row['event'] == 'FREE' and ptr in allocs:
            start, size, tid_start = allocs.pop(ptr)
            dur = ts - start
            if dur > 0:
                records.append({'tid': tid_start, 'start': start, 'dur': dur, 'size': size})

    if not records:
        print(f"[!] No allocation lifetimes found in {trace_path}")
        return

    lifetimes = pd.DataFrame(records)
    lifetimes['logsize'] = np.log1p(lifetimes['size'])
    cmap = plt.cm.plasma
    norm = plt.Normalize(lifetimes['logsize'].min(), lifetimes['logsize'].max())

    plt.figure(figsize=(12, 6))
    for _, r in lifetimes.iterrows():
        plt.barh(r['tid'], r['dur'], left=r['start'], color=cmap(norm(r['logsize'])), height=2.5)

    plt.xlabel("Time (ms)")
    plt.ylabel("Thread ID")
    plt.title(f"Gantt Chart: {os.path.basename(out_dir)}")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    plt.colorbar(sm, label="Allocation size (log bytes)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[✓] Gantt chart saved to {out_path}")

def parse_smaps(path):
    rss = []
    if not os.path.exists(path):
        return np.array([]), np.array([])
    with open(path) as f:
        total = 0
        for line in f:
            if line.strip().lower().startswith("rss:"):
                parts = line.split()
                if len(parts) >= 2:
                    total += int(parts[1])
        rss.append(total)
    return np.arange(len(rss)), np.array(rss)

def plot_workload_impact(df, smapsA=None, smapsB=None, outdir="results"):
    print("[+] Generating workload impact graphs...")
    # Compute cumulative net allocated size over time
    allocs = df[df['event'] == 'ALLOC'].copy()
    frees = df[df['event'] == 'FREE'].copy()

    allocs['bytes'] = allocs['size']
    frees['bytes'] = -frees['size']

    all_events = pd.concat([allocs, frees]).sort_values('ts_ns')
    all_events['cum_bytes'] = all_events['bytes'].cumsum() / (1024*1024)  # MB

    plt.figure(figsize=(10,5))
    plt.plot(all_events['ts_ns'] - all_events['ts_ns'].min(), all_events['cum_bytes'], label='Net Allocated (MB)')
    plt.xlabel('Time (ns offset)')
    plt.ylabel('Allocated Memory (MB)')
    plt.title('Workload Impact — Memory Usage Over Time')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "impact_memory_usage.png"))
    plt.close()
    print("[✓] Saved workload impact plot ->", os.path.join(outdir, "impact_memory_usage.png"))

    # Optional RSS comparison (Approach A vs B)
    if smapsA and smapsB:
        xA, rssA = parse_smaps(smapsA)
        xB, rssB = parse_smaps(smapsB)
        if rssA.size > 0 or rssB.size > 0:
            plt.figure(figsize=(8,5))
            if rssA.size > 0:
                plt.plot(xA, rssA, label="Approach A (Original)")
            if rssB.size > 0:
                plt.plot(xB, rssB, label="Approach B (Replay)")
            plt.xlabel("Snapshot index")
            plt.ylabel("RSS (KB)")
            plt.title("RSS Comparison — Approach A vs B")
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(outdir, "rss_comparison.png"))
            plt.close()
            print("[✓] Saved RSS comparison ->", os.path.join(outdir, "rss_comparison.png"))

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/metrics_viz.py <mftrace_log.csv> [smapsA] [smapsB]")
        sys.exit(1)

    trace_path = sys.argv[1]
    smapsA = sys.argv[2] if len(sys.argv) > 2 else None
    smapsB = sys.argv[3] if len(sys.argv) > 3 else None
    outdir = os.path.dirname(trace_path) or "results"
    os.makedirs(outdir, exist_ok=True)

    df = load_trace(trace_path)
    trace_csv = os.path.join(outdir, "mftrace_log.csv")
    
    plot_gantt_from_trace(trace_csv, outdir)
    plot_workload_impact(df, smapsA, smapsB, outdir)

    print("[✓] All visualization metrics generated in", outdir)

if __name__ == "__main__":
    main()

