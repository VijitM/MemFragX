#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime

def read_smaps(pid):
    try:
        with open(f"/proc/{pid}/smaps", "r") as f:
            return f.read()
    except FileNotFoundError:
        return None

def snapshot_loop(pid, outdir, interval=1.0):
    os.makedirs(outdir, exist_ok=True)
    snap_id = 0
    print(f"[snapshotter] Monitoring PID {pid} every {interval}s... Press Ctrl+C to stop.")
    while True:
        data = read_smaps(pid)
        if data is None:
            print("[snapshotter] Process ended, stopping snapshots.")
            break
        snap_file = os.path.join(outdir, f"smap_{snap_id:04d}.txt")
        with open(snap_file, "w") as f:
            f.write(f"# Snapshot {snap_id} at {datetime.now()}\n")
            f.write(data)
        snap_id += 1
        time.sleep(interval)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: snapshotter.py <pid> <output_dir> [interval_seconds]")
        sys.exit(1)
    pid = int(sys.argv[1])
    outdir = sys.argv[2]
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    snapshot_loop(pid, outdir, interval)

