#!/usr/bin/env python3
"""
metrics_viz.py — Generate memory allocation heatmaps and workload impact graphs
Usage:
  python3 tools/metrics_viz.py <mftrace_log.csv> [smapsA] [smapsB]
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

def plot_heatmap(df, outdir):
    print("[+] Generating heatmap...")
    # Group by thread ID and size bucket
    df['size_kb'] = (df['size'] / 1024).clip(upper=1024*16)  # cap at 16 MB
    bins = np.logspace(0, np.log10(1024*16), 50)
    df['bucket'] = pd.cut(df['size_kb'], bins)
    heat = df[df['event'] == 'ALLOC'].groupby(['tid','bucket']).size().unstack(fill_value=0)

    plt.figure(figsize=(10,6))
    plt.imshow(np.log1p(heat.T), aspect='auto', cmap='viridis', origin='lower')
    plt.colorbar(label='log(alloc count + 1)')
    plt.yticks(range(len(heat.columns)), [str(b) for b in heat.columns], fontsize=6)
    plt.xticks(range(len(heat.index)), heat.index, rotation=90)
    plt.title('Allocation Heatmap (Thread vs. Size Bucket)')
    plt.xlabel('Thread ID')
    plt.ylabel('Allocation Size (KB)')
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "heatmap_allocations.png"))
    plt.close()
    print("[✓] Saved heatmap ->", os.path.join(outdir, "heatmap_allocations.png"))

def parse_smaps(path):
    rss = []
    if not os.path.exists(path):
        return np.array([]), np.array([])
    with open(path) as f:
        total = 0
        for line in f:
            if line.startswith("Rss:"):
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
    plot_heatmap(df, outdir)
    plot_workload_impact(df, smapsA, smapsB, outdir)

    print("[✓] All visualization metrics generated in", outdir)

if __name__ == "__main__":
    main()

