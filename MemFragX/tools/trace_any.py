#!/usr/bin/env python3
"""
Runs any program under the tracer, captures smaps, performs analysis,
and automatically generates & runs the replay (Approach B).
"""

import os
import subprocess
import argparse
import time
import shlex

def run(cmd, **kwargs):
    print(f"[>] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=False, **kwargs)

def main():
    parser = argparse.ArgumentParser(description="Trace and replay any real program using MemFragX.")
    parser.add_argument("--program", required=True, help='Program and args, e.g. "./myapp arg1 arg2"')
    parser.add_argument("--out", default="results/run1", help="Output directory for results")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds to wait before capturing smaps")
    parser.add_argument("--no-replay", action="store_true", help="Skip replay phase (Approach B)")
    args = parser.parse_args()

    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    tracer_path = os.path.join(ROOT, "tracer", "libmftrace.so")
    analysis_script = os.path.join(ROOT, "analysis", "analysis.py")
    replay_gen = os.path.join(ROOT, "tools", "replay_compact.py")

    os.makedirs(args.out, exist_ok=True)
    mftrace_log = os.path.join(args.out, "mftrace_log.csv")
    smaps_path = os.path.join(args.out, "smaps")

    #Trace target program
    env = os.environ.copy()
    env["LD_PRELOAD"] = tracer_path
    env["MFTRACE_LOG"] = mftrace_log

    print(f"[+] Tracing command: {args.program}")
    print(f"[+] Log: {mftrace_log}")
    print(f"[+] Using tracer: {tracer_path}")

    proc = subprocess.Popen(shlex.split(args.program), env=env)
    pid = proc.pid
    print(f"[+] PID: {pid}")

    # Wait a little, capture smaps mid-run
    time.sleep(args.sleep)
    if os.path.exists(f"/proc/{pid}/smaps"):
        try:
            with open(f"/proc/{pid}/smaps") as src, open(smaps_path, "w") as dst:
                dst.write(src.read())
            print(f"[✓] Captured smaps -> {smaps_path}")
        except PermissionError:
            print("[!] Permission denied reading /proc/<pid>/smaps")
    else:
        print("[!] Process exited before smaps capture")

    proc.wait()
    print(f"[✓] Program exited with code {proc.returncode}")

    # --- Step 2: Run analysis (Approach A) ---
    print("[+] Running analysis (Approach A)...")
    run(["python3", analysis_script, mftrace_log, smaps_path])

    if args.no_replay:
        print("[✓] Done (skipped replay phase).")
        return

    # --- Step 3: Generate replay program (Approach B) ---
    replay_c = os.path.join(args.out, "replay.c")
    print("[+] Generating replay program...")
    run(["python3", replay_gen, mftrace_log, replay_c])

    if not os.path.exists(replay_c):
        print("[!] Replay source not created; aborting.")
        return

    #Compile and run replay
    replay_bin = os.path.join(args.out, "replay")
    print("[+] Compiling replay...")
    run(["gcc", "-O2", replay_c, "-o", replay_bin])

    if not os.path.exists(replay_bin):
        print("[!] Replay binary missing; aborting.")
        return

    print("[+] Running replay (Approach B)...")
    replay_proc = subprocess.Popen([replay_bin])
    pid_b = replay_proc.pid
    time.sleep(2)

    smaps_b = os.path.join(args.out, "smaps_replay")
    if os.path.exists(f"/proc/{pid_b}/smaps"):
        try:
            with open(f"/proc/{pid_b}/smaps") as src, open(smaps_b, "w") as dst:
                dst.write(src.read())
            print(f"[✓] Captured smaps for replay -> {smaps_b}")
        except PermissionError:
            print("[!] Permission denied reading replay smaps")

    replay_proc.wait()
    print(f"[✓] Replay finished with code {replay_proc.returncode}")

    # Compare results (A vs B)
    print("[+] Running RSS/fragmentation comparison...")
    run(["python3", analysis_script, mftrace_log, smaps_path, smaps_b])

    print(f"[✓] Full trace+replay pipeline complete.\nResults stored in: {args.out}")

    viz_script = os.path.join(ROOT, "tools", "metrics_viz.py")
    run(["python3", viz_script, mftrace_log, smaps_path, smaps_b])


if __name__ == "__main__":
    main()

